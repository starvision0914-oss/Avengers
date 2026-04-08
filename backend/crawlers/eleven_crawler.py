"""
11번가 광고비 크롤러
- soffice.11st.co.kr 로그인
- 셀러포인트 내역 XLS 다운로드
- 파싱 후 DB 저장
"""
import os
import re
import json
import time
import logging
import shutil
from pathlib import Path
from datetime import datetime
from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import redis as redis_client

from .browser import create_driver, stop_display
from .utils import parse_int, classify_11st_description, wait_for_download

logger = logging.getLogger('crawler')

LOGIN_URL = 'https://login.11st.co.kr/auth/front/selleroffice/login.tmall'
COST_URL = 'https://soffice.11st.co.kr/view/8201'
DOWNLOAD_BASE = Path('/tmp/avengers_11st_downloads')

EXCEL_XPATHS = [
    '/html/body/form[1]/div/div[1]/div[4]/div[2]/a',
    '//*[@id="frmSearch"]//a[contains(@class,"excel")]',
    '//a[contains(text(),"엑셀")]',
    '//a[contains(text(),"Excel")]',
]
SEARCH_BTN_XPATH = '//*[@id="frmSearch"]/div/div[1]/div[3]/div[1]/div[2]/div[2]/div/button'


def _wait_for_otp_redis(timeout=60):
    """Redis pub/sub → DB 조회로 OTP 코드 추출 (ai100 방식)"""
    r = redis_client.Redis(
        host=os.environ.get('REDIS_HOST', 'localhost'),
        port=int(os.environ.get('REDIS_PORT', 6379)),
        db=int(os.environ.get('REDIS_DB', 0)),
        decode_responses=True,
    )
    channel = os.environ.get('REDIS_CHANNEL', 'sms:new')
    ps = r.pubsub()
    ps.subscribe(channel)

    start = time.time()
    while time.time() - start < timeout:
        msg = ps.get_message(timeout=1)
        if msg and msg['type'] == 'message':
            try:
                payload = json.loads(msg['data'])
                last_id = payload.get('last_id')
                if not last_id:
                    continue

                # DB에서 SMS 내용 조회
                import django
                django.setup()
                from apps.cpc.models import ReceivedSmsMessage
                sms = ReceivedSmsMessage.objects.filter(id=last_id).first()
                if not sms:
                    continue

                sms_text = sms.message or ''
                logger.info(f'[OTP] SMS 수신 (id={last_id}): {sms_text[:50]}...')

                # 11번가 인증번호 필터
                if '인증' in sms_text or '인증번호' in sms_text:
                    match = re.search(r'\[(\d{6})\]', sms_text)
                    if match:
                        ps.unsubscribe()
                        logger.info(f'[OTP] 코드 추출: {match.group(1)}')
                        return match.group(1)
            except Exception as e:
                logger.warning(f'[OTP] 처리 오류: {e}')
    ps.unsubscribe()
    return None


def _do_login(driver, login_id, password):
    driver.get(LOGIN_URL)
    time.sleep(3)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'loginName'))
        )

        id_field = driver.find_element(By.ID, 'loginName')
        id_field.click()
        time.sleep(0.2)
        id_field.send_keys(login_id)
        time.sleep(0.3)

        pw_field = driver.find_element(By.ID, 'passWord')
        pw_field.click()
        time.sleep(0.2)
        pw_field.send_keys(password)
        time.sleep(0.5)

        driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
        time.sleep(5)

        # alert 처리
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            alert.accept()
            time.sleep(1)
            if '패스워드' in alert_text or '비밀번호' in alert_text or '아이디' in alert_text:
                logger.error(f'[11st:{login_id}] 로그인 실패: {alert_text}')
                return False
        except Exception:
            pass

        # OTP 체크
        if 'otpLoginForm' in driver.current_url:
            logger.info(f'[11st:{login_id}] OTP 인증 필요, Redis 대기...')
            # Kakao OTP 버튼 클릭
            try:
                kakao_btn = driver.find_element(By.XPATH, '//*[@id="auth_kakao_otp"]/button')
                kakao_btn.click()
                time.sleep(1)
                try:
                    alert = driver.switch_to.alert
                    alert.accept()
                except Exception:
                    pass
            except Exception:
                pass

            otp_code = _wait_for_otp_redis(timeout=60)
            if otp_code:
                otp_input = driver.find_element(By.XPATH, '//*[@id="auth_num_kakao"]')
                otp_input.send_keys(otp_code)
                confirm_btn = driver.find_element(By.XPATH, '//*[@id="auth_kakao_otp"]/div/button')
                confirm_btn.click()
                time.sleep(3)
                if 'soffice.11st.co.kr' in driver.current_url:
                    return True
            logger.warning(f'[11st:{login_id}] OTP 인증 실패')
            return False

        # 로그인 성공 확인
        if 'soffice.11st.co.kr' in driver.current_url or 'selleroffice' in driver.current_url:
            return True

        return False
    except Exception as e:
        logger.error(f'[{login_id}] 로그인 실패: {e}')
        return False


def _download_cost_xls(driver, download_dir, login_id):
    # CDP 명령으로 다운로드 경로 설정
    driver.execute_cdp_cmd('Page.setDownloadBehavior', {
        'behavior': 'allow', 'downloadPath': str(download_dir)
    })

    driver.get(COST_URL)
    time.sleep(3)

    try:
        # iframe 전환
        iframe = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//iframe[contains(@id,'8201')]"))
        )
        driver.switch_to.frame(iframe)
        time.sleep(2)

        # 기간 선택: 최근한달
        try:
            date_select = driver.find_element(By.NAME, 'searchApplyDt')
            for option in date_select.find_elements(By.TAG_NAME, 'option'):
                if '최근한달' in option.text or '최근 한달' in option.text:
                    option.click()
                    break
        except Exception:
            pass

        # 검색 버튼
        try:
            search_btn = driver.find_element(By.XPATH, SEARCH_BTN_XPATH)
            search_btn.click()
            time.sleep(3)
        except Exception:
            pass

        # 엑셀 다운로드 버튼 - 여러 XPath 시도
        excel_clicked = False
        for xpath in EXCEL_XPATHS:
            try:
                excel_btn = driver.find_element(By.XPATH, xpath)
                excel_btn.click()
                excel_clicked = True
                break
            except Exception:
                continue

        if not excel_clicked:
            logger.error(f'[{login_id}] 엑셀 버튼 못 찾음')
            driver.switch_to.default_content()
            return None

        driver.switch_to.default_content()

        # 다운로드 대기
        filepath = wait_for_download(download_dir, timeout=60)
        return filepath
    except Exception as e:
        logger.error(f'[{login_id}] 다운로드 실패: {e}')
        driver.switch_to.default_content()
        return None


def _parse_and_save_xls(filepath, seller_id):
    from apps.cpc.models import ElevenCostHistory

    # .xls는 xlrd, .xlsx는 openpyxl
    filepath = str(filepath)
    rows = []
    try:
        if filepath.endswith('.xls'):
            import xlrd
            wk = xlrd.open_workbook(filepath)
            ws = wk.sheet_by_index(0)
            rows = [ws.row_values(i) for i in range(ws.nrows)]
        else:
            import openpyxl
            wb = openpyxl.load_workbook(filepath)
            rows = list(wb.active.iter_rows(values_only=True))
    except Exception as e:
        logger.error(f'파일 읽기 실패: {e}')
        return 0

    if not rows:
        return 0

    # 헤더 행 찾기
    header_idx = None
    for i, row in enumerate(rows):
        row_str = ' '.join(str(c or '') for c in row)
        if '거래일시' in row_str or '거래항목' in row_str:
            header_idx = i
            break

    if header_idx is None:
        header_idx = 1

    headers = [str(c or '').strip() for c in rows[header_idx]]

    col_map = {}
    for i, h in enumerate(headers):
        if '거래일시' in h:
            col_map['datetime'] = i
        elif '거래항목' in h or '거래내용' in h:
            col_map['desc'] = i
        elif '거래금액' in h:
            col_map['amount'] = i
        elif '잔여금액' in h or '잔액' in h:
            col_map['balance'] = i

    saved = 0
    for row in rows[header_idx + 1:]:
        if not row or not row[0]:
            continue

        try:
            dt_val = row[col_map.get('datetime', 0)]
            if isinstance(dt_val, datetime):
                dt = dt_val
            else:
                dt_str = str(dt_val)
                dt = None
                for fmt in ['%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y.%m.%d %H:%M:%S']:
                    try:
                        dt = datetime.strptime(dt_str, fmt)
                        break
                    except ValueError:
                        continue
                if not dt:
                    continue

            desc = str(row[col_map.get('desc', 1)] or '')
            amount = parse_int(row[col_map.get('amount', 2)])
            balance = parse_int(row[col_map.get('balance', 3)])

            ElevenCostHistory.objects.update_or_create(
                seller_id=seller_id,
                transaction_datetime=timezone.make_aware(dt) if timezone.is_naive(dt) else dt,
                defaults={
                    'transaction_type': classify_11st_description(desc),
                    'raw_description': desc[:255],
                    'amount': amount,
                    'balance': balance,
                }
            )
            saved += 1
        except Exception as e:
            logger.warning(f'행 파싱 오류: {e}')
            continue

    return saved


def run_all_accounts(log_fn=None, account_filter=None):
    from apps.cpc.models import CrawlerAccount, CrawlerLog

    accounts = CrawlerAccount.objects.filter(platform='11st', is_active=True)
    if account_filter:
        accounts = accounts.filter(login_id__in=account_filter)

    if not accounts.exists():
        msg = '활성 11번가 계정이 없습니다.'
        if log_fn:
            log_fn(msg)
        return {'collected': 0, 'failed': 0}

    collected, failed = 0, 0
    driver = None

    try:
        driver = create_driver()

        for account in accounts:
            if account.crawling_status == '차단됨':
                if log_fn: log_fn(f'[11st:{account.login_id}] 차단됨 - 건너뜀')
                continue

            login_id = account.login_id

            def log(msg):
                logger.info(f'[11st:{login_id}] {msg}')
                if log_fn:
                    log_fn(f'[11st:{login_id}] {msg}')

            try:
                # 쿠키 삭제 전 about:blank으로 이동하여 기존 세션 alert 방지
                try:
                    driver.get('about:blank')
                    time.sleep(0.5)
                except Exception:
                    pass
                try:
                    alert = driver.switch_to.alert
                    alert.accept()
                except Exception:
                    pass
                driver.delete_all_cookies()

                log('로그인 시도...')
                if not _do_login(driver, login_id, account.password_enc):
                    raise Exception('로그인 실패')
                log('로그인 성공')

                # 다운로드 디렉토리 준비
                dl_dir = DOWNLOAD_BASE / login_id
                dl_dir.mkdir(parents=True, exist_ok=True)
                # 이전 파일 정리
                for f in dl_dir.iterdir():
                    f.unlink(missing_ok=True)

                # XLS 다운로드
                log('광고비 내역 다운로드 중...')
                filepath = _download_cost_xls(driver, str(dl_dir), login_id)

                if filepath:
                    log(f'파싱 중: {filepath.name}')
                    saved = _parse_and_save_xls(filepath, login_id)
                    log(f'{saved}건 저장 완료')

                    account.fail_count = 0
                    account.crawling_status = '정상'
                    account.last_crawled_at = timezone.now()
                    account.save()
                    collected += 1

                    CrawlerLog.objects.create(
                        platform='11st', level='success',
                        message=f'{saved}건 저장 완료',
                        account_id=login_id
                    )
                else:
                    raise Exception('다운로드 실패')

            except Exception as e:
                account.fail_count += 1
                if account.fail_count >= 30:
                    account.crawling_status = '차단됨'
                account.save()
                failed += 1

                CrawlerLog.objects.create(
                    platform='11st', level='error',
                    message=str(e),
                    account_id=login_id
                )
                log(f'실패: {e}')
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        stop_display()

    summary = f'11번가 수집 완료: 성공={collected} 실패={failed}'
    if log_fn:
        log_fn(summary)

    return {'collected': collected, 'failed': failed}
