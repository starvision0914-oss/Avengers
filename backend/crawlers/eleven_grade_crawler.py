"""11번가 셀러 등급 크롤러 - soffice.11st.co.kr"""
import os
import re
import json
import time
import logging
import redis as redis_client
from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .browser import create_driver, create_headless_driver, stop_display

logger = logging.getLogger('crawler')
LOGIN_URL = 'https://login.11st.co.kr/auth/front/selleroffice/login.tmall'
GRADE_URL = 'https://soffice.11st.co.kr/view/5004'

def _wait_for_otp_redis(timeout=300):
    """Redis pub/sub → DB 조회로 OTP 코드 추출 (eleven_crawler.py와 동일)"""
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
                import django
                django.setup()
                from apps.cpc.models import ReceivedSmsMessage
                sms = ReceivedSmsMessage.objects.filter(id=last_id).first()
                if not sms:
                    continue
                sms_text = sms.message or ''
                code = None
                m = re.search(r'인증번호\D*\[?\s*(\d{6})\s*\]?', sms_text)
                if m:
                    code = m.group(1)
                else:
                    m = re.search(r'\[(\d{6})\]', sms_text)
                    if m:
                        code = m.group(1)
                if code:
                    ps.unsubscribe()
                    logger.info(f'[OTP] 코드 추출: {code}')
                    return code
            except Exception:
                pass
    ps.unsubscribe()
    return None


def _login(driver, login_id, password):
    """eleven_crawler.py와 동일한 로그인 로직 (OTP + 캠페인 우회)"""
    driver.get(LOGIN_URL)
    time.sleep(3)
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'loginName')))
        driver.find_element(By.ID, 'loginName').click()
        time.sleep(0.2)
        driver.find_element(By.ID, 'loginName').send_keys(login_id)
        driver.find_element(By.ID, 'passWord').click()
        time.sleep(0.2)
        driver.find_element(By.ID, 'passWord').send_keys(password)
        driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
        time.sleep(5)

        # alert 처리
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            alert.accept()
            if '패스워드' in alert_text or '비밀번호' in alert_text or '아이디' in alert_text:
                return False
        except Exception:
            pass

        # 캠페인 페이지 우회
        if 'passwordCampaign' in driver.current_url:
            logger.info(f'[11st등급:{login_id}] 캠페인 우회')
            try:
                btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, 'nextTime')))
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(3)
                try:
                    a = driver.switch_to.alert; a.accept(); time.sleep(2)
                except: pass
            except: pass

        if 'soffice.11st.co.kr' not in driver.current_url and 'otpLoginForm' not in driver.current_url:
            try:
                driver.get('https://soffice.11st.co.kr/view/main')
                time.sleep(3)
            except: pass

        # OTP
        if 'otpLoginForm' in driver.current_url:
            logger.info(f'[11st등급:{login_id}] OTP 페이지')
            try:
                radio = driver.find_element(By.ID, 'auth_type_01')
                if not radio.is_selected():
                    driver.execute_script("arguments[0].click();", radio)
            except: pass

            send_clicked = False
            for sel in [
                "//button[@onclick='requestOTP();' and contains(@data-log-body, 'cell') and not(@id)]",
                "//button[normalize-space(text())='인증번호 전송' and contains(@data-log-body,'cell')]",
            ]:
                try:
                    btn = driver.find_element(By.XPATH, sel)
                    driver.execute_script("arguments[0].click();", btn)
                    send_clicked = True
                    logger.info(f'[11st등급:{login_id}] 인증번호 전송 클릭')
                    break
                except: continue
            if not send_clicked:
                try:
                    btn = driver.find_element(By.XPATH, '//*[@id="auth_kakao_otp"]/button')
                    btn.click()
                except: pass

            time.sleep(1.5)
            try:
                a = driver.switch_to.alert; logger.info(f'alert: {a.text}'); a.accept()
            except: pass

            logger.info(f'[11st등급:{login_id}] OTP 대기 (300초)...')
            otp_code = _wait_for_otp_redis(timeout=300)
            if otp_code:
                logger.info(f'[11st등급:{login_id}] OTP 수신: {otp_code}')
                try:
                    inp = driver.find_element(By.ID, 'auth_num_kakao')
                    inp.clear(); inp.send_keys(otp_code)
                except: pass
                for sel in ["//button[@onclick='login();' and contains(@data-log-body,'cell')]"]:
                    try:
                        btn = driver.find_element(By.XPATH, sel)
                        driver.execute_script("arguments[0].click();", btn)
                        break
                    except: continue
                time.sleep(4)
                try:
                    a = driver.switch_to.alert; a.accept(); time.sleep(2)
                except: pass
                if 'soffice.11st.co.kr' in driver.current_url:
                    logger.info(f'[11st등급:{login_id}] OTP 인증 성공')
                    return True
            logger.warning(f'[11st등급:{login_id}] OTP 실패')
            return False

        if 'soffice.11st.co.kr' in driver.current_url or 'selleroffice' in driver.current_url:
            return True
        return False
    except Exception as e:
        logger.error(f'[11st등급:{login_id}] 로그인 실패: {e}')
        return False

def _close_popups(driver):
    for sel in ['.popup-close', '.btn-close', '.layer-close']:
        for el in driver.find_elements(By.CSS_SELECTOR, sel):
            try: el.click()
            except: pass
    for btn in driver.find_elements(By.TAG_NAME, 'button'):
        if btn.text.strip() in ('닫기', 'close', '확인'):
            try: btn.click()
            except: pass
    try:
        alert = driver.switch_to.alert
        alert.accept()
    except: pass

def _collect_grade(driver, login_id, seller_name='', log_fn=None):
    def log(m):
        if log_fn: log_fn(f'[11st등급:{login_id}] {m}')

    driver.get(GRADE_URL)
    time.sleep(3)
    _close_popups(driver)

    grade, grade_img_src, required_sales, grade_message = None, '', None, ''

    try:
        iframe = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//iframe[contains(@id,'5004')]"))
        )
        driver.switch_to.frame(iframe)
        time.sleep(2)

        # 등급 이미지에서 등급 번호 추출
        try:
            img = driver.find_element(By.XPATH, '//*[@id="gradeB_c"]/img')
            grade_img_src = img.get_attribute('src') or ''
            m = re.search(r'seller_grade(\d+)', grade_img_src)
            if m:
                grade = int(m.group(1))
        except Exception:
            pass

        # 필요 매출액
        try:
            el = driver.find_element(By.XPATH,
                '//*[@id="form1"]/div[10]/div/div[7]/table/tbody/tr/td[4]/table/tbody/tr[2]/td/b')
            val = re.sub(r'[^\d]', '', el.text)
            if val and int(val) > 1000:
                required_sales = int(val)
        except Exception:
            # fallback: 모든 b 태그에서 가장 큰 숫자
            try:
                for b in driver.find_elements(By.TAG_NAME, 'b'):
                    val = re.sub(r'[^\d]', '', b.text)
                    if val and int(val) > 100000:
                        if required_sales is None or int(val) > required_sales:
                            required_sales = int(val)
            except Exception:
                pass

        # 등급 메시지
        try:
            for el in driver.find_elements(By.TAG_NAME, 'span') + driver.find_elements(By.TAG_NAME, 'td'):
                text = el.text.strip()
                if '등급' in text and any(kw in text for kw in ['하향', '유지', '조정', '판매활동']):
                    grade_message = text[:255]
                    break
        except Exception:
            pass

        driver.switch_to.default_content()
    except Exception as e:
        log(f'등급 추출 실패: {e}')
        try: driver.switch_to.default_content()
        except: pass

    log(f'등급={grade} 필요매출={required_sales} 메시지={grade_message[:30]}')
    return {
        'eleven_id': login_id, 'seller_name': seller_name,
        'grade': grade, 'grade_img_src': grade_img_src,
        'required_sales': required_sales, 'grade_message': grade_message,
        'collected_at': timezone.now(),
    }

def run_all_accounts(log_fn=None, account_filter=None, force=False):
    import random
    from apps.cpc.models import CrawlerAccount, ElevenSellerGrade, CrawlerLog
    from apps.cpc import eleven_block_guard as guard

    # 글로벌 차단 락 확인
    if guard.guard_and_skip('grade crawler'):
        if log_fn: log_fn('⛔ 11번가 글로벌 차단 모드 — grade 크롤러 스킵')
        return {'collected': 0, 'failed': 0, 'aborted_due_to_global_block': True}

    # api 키 보유 계정만 대상 (운영 정책: api 없는 계정은 등급 수집 안 함)
    qs = (CrawlerAccount.objects.filter(platform='11st', is_active=True)
          .exclude(crawling_status__in=['차단됨', '실패'])
          .exclude(api_key=''))
    if account_filter:
        qs = qs.filter(login_id__in=account_filter)
    all_accounts = list(qs)
    if not all_accounts:
        if log_fn: log_fn('활성 11번가 계정 없음')
        return {'collected': 0, 'failed': 0}

    # 차단 회피 보수적 페이싱
    INTER_ACCOUNT_SLEEP = (30.0, 90.0)
    CIRCUIT_BREAKER_THRESHOLD = 5
    SKIP_RECENT_HOURS = 24  # 등급은 자주 안 바뀌므로 24시간
    MAX_CONNECT_ATTEMPTS = 3  # 계정당 접속 최대 3회 시도, 3회 실패 시 중지→다음 계정

    # 신선도 필터 — 최근 등급 수집한 계정 제외
    skipped_recent = []
    accounts = []
    recent_grade_map = {}
    for g in ElevenSellerGrade.objects.order_by('eleven_id', '-collected_at'):
        recent_grade_map.setdefault(g.eleven_id, g.collected_at)
    for a in all_accounts:
        if (not force) and guard.is_recently_synced(recent_grade_map.get(a.login_id), hours=SKIP_RECENT_HOURS):
            skipped_recent.append(a.login_id)
        else:
            accounts.append(a)
    total_accounts = len(accounts)
    if log_fn:
        log_fn(f'[grade] 최근 {SKIP_RECENT_HOURS}h 내 수집 {len(skipped_recent)}계정 스킵, 대상 {total_accounts}계정')

    results = []
    failed = 0
    consecutive_block = 0
    aborted = False
    from .browser import _kill_stale_chrome
    from . import eleven_crawler as _ec

    for idx, acct in enumerate(accounts, 1):
        # 매 계정 시작 전 글로벌 락 체크
        if guard.guard_and_skip(f'grade[{acct.login_id}]'):
            aborted = True
            break

        if acct.crawling_status in ('차단됨', '실패'):
            if log_fn: log_fn(f'[11st등급:{acct.login_id}] {acct.crawling_status} - 건너뜀')
            continue

        driver = None
        # ── 접속(로그인) 단계: 최대 3회 시도. 3회 실패 시 중지→다음 계정 ──
        logged_in = False
        used_cookie = False
        for attempt in range(1, MAX_CONNECT_ATTEMPTS + 1):
            if guard.guard_and_skip(f'grade[{acct.login_id}] 접속'):
                aborted = True
                break
            try:
                if driver is None:
                    _kill_stale_chrome()
                    driver = create_driver()
                # 1) 쿠키 로그인 (1회차에만, OTP 우회)
                if attempt == 1:
                    try:
                        ck = _ec._try_cookie_login(driver, acct)
                    except Exception:
                        ck = False
                    if ck is None:
                        try: driver.quit()
                        except: pass
                        _kill_stale_chrome()
                        driver = create_driver()
                        ck = False
                    if ck:
                        logged_in = True
                        used_cookie = True
                        break
                # 2) 일반 로그인 (OTP 트리거 가능)
                if _login(driver, acct.login_id, acct.password_enc):
                    logged_in = True
                    try: _ec._save_cookies(driver, acct)
                    except Exception: pass
                    break
                raise Exception('로그인 실패/OTP')
            except Exception as le:
                if log_fn: log_fn(f'[11st등급:{acct.login_id}] 접속 실패 {attempt}/{MAX_CONNECT_ATTEMPTS}: {str(le)[:120]}')
                if guard.is_block_signal(le):
                    consecutive_block += 1
                    if consecutive_block >= CIRCUIT_BREAKER_THRESHOLD:
                        guard.report_signal(le, source='grade crawler')
                        aborted = True
                        break
                try:
                    if driver: driver.quit()
                except: pass
                _kill_stale_chrome()
                driver = None
                if attempt < MAX_CONNECT_ATTEMPTS:
                    time.sleep(random.uniform(2.0, 4.0))

        if aborted:
            if driver:
                try: driver.quit()
                except: pass
            break

        if not logged_in:
            # ── 접속 3회 실패 → 반드시 중지하고 다음 계정으로 ──
            failed += 1
            acct.fail_count = (acct.fail_count or 0) + 1
            acct.save(update_fields=['fail_count'])
            acct.mark_connect_failed()
            CrawlerLog.objects.create(
                platform='11st', level='error',
                message=f'등급 접속 {MAX_CONNECT_ATTEMPTS}회 실패 → 중지(다음 계정), 상태={acct.crawling_status}',
                account_id=acct.login_id)
            if log_fn: log_fn(f'[11st등급:{acct.login_id}] ⛔ 접속 {MAX_CONNECT_ATTEMPTS}회 실패 — 다음 계정 (상태={acct.crawling_status})')
            try:
                guard._send_telegram_alert(
                    f'⚠️ [11번가 등급 접속실패]\n계정: {acct.login_id} ({acct.seller_name})\n'
                    f'접속 {MAX_CONNECT_ATTEMPTS}회 연속 실패 → 중지하고 다음 계정. 상태: {acct.crawling_status}')
            except Exception:
                pass
            if driver:
                try: driver.quit()
                except: pass
            if idx < total_accounts:
                time.sleep(random.uniform(*INTER_ACCOUNT_SLEEP))
            continue

        # ── 접속 성공 → 등급 수집 ──
        acct.reset_connect_fail()
        consecutive_block = 0
        try:
            if used_cookie and log_fn:
                log_fn(f'[11st등급:{acct.login_id}] 쿠키 재사용 (OTP 우회)')
            result = _collect_grade(driver, acct.login_id, acct.seller_name, log_fn)
            if result:
                results.append(result)
        except Exception as e:
            failed += 1
            if log_fn: log_fn(f'[11st등급:{acct.login_id}] 수집 오류: {e}')
            try:
                guard._send_telegram_alert(
                    f'⚠️ [11번가 등급 수집오류]\n계정: {acct.login_id} ({acct.seller_name})\n{str(e)[:150]}')
            except Exception:
                pass
        finally:
            if driver:
                try: driver.quit()
                except: pass

        # 사람 패턴: 마지막 계정 아니면 잠시 대기
        if idx < total_accounts:
            wait = random.uniform(*INTER_ACCOUNT_SLEEP)
            if log_fn: log_fn(f'[11st등급] 다음 계정까지 {wait:.1f}s 대기')
            time.sleep(wait)
    stop_display()

    for r in results:
        ElevenSellerGrade.objects.create(**r)

    suffix = ' (차단신호로 조기 중단)' if aborted else ''
    CrawlerLog.objects.create(platform='11st', level='info', message=f'등급 수집: {len(results)}건 / 실패 {failed}건{suffix}')
    if log_fn: log_fn(f'11번가 등급 수집 완료: {len(results)}건 / 실패 {failed}건{suffix}')
    return {
        'collected': len(results),
        'failed': failed,
        'aborted_due_to_block': aborted,
        'skipped_recent': len(skipped_recent),
    }
