"""
11번가 광고비 크롤러
- soffice.11st.co.kr 로그인
- 셀러포인트 내역 XLS 다운로드
- 파싱 후 DB 저장
"""
import os
import time
import logging
import shutil
from pathlib import Path
from datetime import datetime
from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .browser import create_driver, stop_display
from .utils import parse_int, classify_11st_description, wait_for_download

logger = logging.getLogger('crawler')

LOGIN_URL = 'https://login.11st.co.kr/auth/front/selleroffice/login.tmall'
COST_URL = 'https://soffice.11st.co.kr/view/8201'
DOWNLOAD_BASE = Path('/tmp/avengers_11st_downloads')


def _do_login(driver, login_id, password):
    driver.get(LOGIN_URL)
    time.sleep(2)

    try:
        id_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'loginName'))
        )
        id_field.clear()
        id_field.send_keys(login_id)

        pw_field = driver.find_element(By.ID, 'passWord')
        pw_field.clear()
        pw_field.send_keys(password)

        submit = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        submit.click()

        time.sleep(3)

        # OTP 체크
        if 'otpLoginForm' in driver.current_url:
            logger.warning(f'[{login_id}] OTP 인증 필요 - 건너뜀')
            return False

        # 로그인 성공 확인
        if 'soffice.11st.co.kr' in driver.current_url or 'selleroffice' in driver.current_url:
            return True

        return False
    except Exception as e:
        logger.error(f'[{login_id}] 로그인 실패: {e}')
        return False


def _download_cost_xls(driver, download_dir, login_id):
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
            search_btn = driver.find_element(By.XPATH, '//*[@id="frmSearch"]//button')
            search_btn.click()
            time.sleep(3)
        except Exception:
            pass

        # 엑셀 다운로드 버튼
        try:
            excel_btn = driver.find_element(By.XPATH, '//a[contains(@class,"excel") or contains(text(),"엑셀") or contains(text(),"Excel")]')
            excel_btn.click()
        except Exception:
            # 대체 XPath
            try:
                excel_btn = driver.find_element(By.XPATH, '/html/body/form[1]/div/div[1]/div[4]/div[2]/a')
                excel_btn.click()
            except Exception as e:
                logger.error(f'[{login_id}] 엑셀 버튼 못 찾음: {e}')
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
    import openpyxl

    try:
        wb = openpyxl.load_workbook(filepath)
        ws = wb.active

        rows = list(ws.iter_rows(values_only=True))
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
            header_idx = 1  # 기본값

        headers = [str(c or '').strip() for c in rows[header_idx]]

        # 컬럼 인덱스 매핑
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
                    for fmt in ['%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y.%m.%d %H:%M:%S']:
                        try:
                            dt = datetime.strptime(dt_str, fmt)
                            break
                        except ValueError:
                            continue
                    else:
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
    except Exception as e:
        logger.error(f'XLS 파싱 실패: {e}')
        return 0


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
            login_id = account.login_id

            def log(msg):
                logger.info(f'[11st:{login_id}] {msg}')
                if log_fn:
                    log_fn(f'[11st:{login_id}] {msg}')

            try:
                driver.delete_all_cookies()

                log('로그인 시도...')
                if not _do_login(driver, login_id, account.password):
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
                if account.fail_count >= 5:
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
