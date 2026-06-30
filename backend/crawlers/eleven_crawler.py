"""
11번가 통합 크롤러 — 1회 로그인으로 오피스 현황 + 광고비 XLS 수집
"""
import os
import re
import json
import time
import logging
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import redis as redis_client

from .browser import create_driver, stop_display
from .utils import parse_int, classify_11st_description, wait_for_download

logger = logging.getLogger('crawler')

LOGIN_URL = 'https://login.11st.co.kr/auth/front/selleroffice/login.tmall'
COST_URL_SELLERPOINT = 'https://soffice.11st.co.kr/view/8201'
COST_URL_SELLERCASH = 'https://soffice.11st.co.kr/view/8301'
DOWNLOAD_BASE = Path('/tmp/avengers_11st_downloads')

# 쿠키 캐시 TTL (시간) — 11번가는 보통 6~8시간 후 세션 만료. 안전하게 4시간.
COOKIE_TTL_HOURS = 72   # 쿠키 유효 3일 — 크롤이 주기적으로 돌면 롤포워드되어 OTP 최소화

# 쿠키 재사용 여부 — True: 유효 쿠키면 빠른 로그인(로그인 부하↓ = IP 차단 위험도↓, 속도↑).
# 안전장치: _try_cookie_login 이 soffice 도달 URL을 검증하고, 죽은 쿠키면 자동으로 풀로그인 폴백(1058~1088줄).
# 계정간 대기/페이싱은 그대로 유지(보수적) — IP 차단 방지 최우선.
USE_COOKIE_LOGIN = True

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

                # 11번가 인증번호 추출:
                # 메시지 형식: "[11번가] 인증번호 [206312]을 입력해 주세요."
                # 패턴 우선순위:
                #   1) 인증번호 키워드 뒤 [XXXXXX]
                #   2) 메시지 어디든 [XXXXXX]
                #   3) 메시지 내 모든 6자리 숫자 중 마지막
                code = None
                m = re.search(r'인증번호\D*\[?\s*(\d{6})\s*\]?', sms_text)
                if m:
                    code = m.group(1)
                else:
                    m = re.search(r'\[(\d{6})\]', sms_text)
                    if m:
                        code = m.group(1)
                    else:
                        all6 = re.findall(r'\d{6}', sms_text)
                        if all6:
                            code = all6[-1]
                if code:
                    ps.unsubscribe()
                    logger.info(f'[OTP] 코드 추출: {code}')
                    return code
            except Exception as e:
                logger.warning(f'[OTP] 처리 오류: {e}')
    ps.unsubscribe()
    return None


def _otp_from_adb_notification(since_ms):
    """폰 알림(adb dumpsys notification)에서 11번가 OTP를 읽음.
    OTP가 RCS/푸시로 와서 문자함(content://sms)에 안 들어가는 경우 대응.
    since_ms 이후 도착한 가장 최신 인증번호(6자리) 반환."""
    import subprocess
    try:
        out = subprocess.run(['adb', 'shell', 'dumpsys', 'notification', '--noredact'],
                             capture_output=True, text=True, timeout=25).stdout
    except Exception as e:
        logger.warning(f'[OTP] adb 알림 조회 실패: {e}')
        return None
    best, best_t = None, since_ms
    # 패턴: ...인증번호 [812131]... time=1780984670165
    for m in re.finditer(r'인증번호\s*\[(\d{6})\][^}]*?time=(\d{13})', out, re.DOTALL):
        code, t = m.group(1), int(m.group(2))
        if t > best_t:
            best_t, best = t, code
    return best


def _otp_from_db(since_ms):
    """앱(smsApp)이 네트워크로 서버에 푸시한 OTP SMS를 DB에서 직접 조회 — USB/adb 불필요.
    since_ms 이후 도착한 11번가 인증번호(6자리)를 최신순으로 찾는다.
    11번가 OTP가 [Web발신] 일반 SMS로도 와서 ReceivedSmsMessage에 적재되므로 USB 없이도 인증 가능."""
    try:
        import datetime as _dt
        from django.utils import timezone as _tz
        from apps.cpc.models import ReceivedSmsMessage
        since = _dt.datetime.fromtimestamp(since_ms / 1000.0, tz=_dt.timezone.utc) if since_ms \
            else _tz.now() - _dt.timedelta(minutes=5)
        for sms in ReceivedSmsMessage.objects.filter(
                received_at__gte=since, message__icontains='인증번호').order_by('-id')[:15]:
            txt = sms.message or ''
            if '11번가' not in txt:
                continue
            m = re.search(r'인증번호\D*\[?\s*(\d{6})\s*\]?', txt)
            if m:
                return m.group(1)
    except Exception as e:
        logger.warning(f'[OTP] DB 조회 실패: {e}')
    return None


def _wait_for_otp_any(since_ms, timeout=180):
    """OTP 대기 — DB(smsApp 네트워크 푸시, USB불필요) 우선, 폰 알림(adb, USB) 보조.
    since_ms 이후 도착분만 인정. USB 없이도 DB 경로만으로 인증 완료 가능."""
    start = time.time()
    while time.time() - start < timeout:
        code = _otp_from_db(since_ms)                 # 앱푸시 SMS(USB 불필요) — 주경로
        if code:
            logger.info(f'[OTP] DB(앱푸시)에서 추출: {code}')
            return code
        code = _otp_from_adb_notification(since_ms)   # 폰 알림(USB 연결 시 보조)
        if code:
            logger.info(f'[OTP] 알림에서 추출: {code}')
            return code
        time.sleep(3)
    return None


def _is_chrome_dead(e):
    """Chrome 프로세스 자체 문제인지 판별 (서버 차단이 아닌 로컬 이슈)"""
    s = str(e)
    return any(k in s for k in (
        'Timed out receiving message from renderer',
        'chrome not reachable', 'session deleted',
        'invalid session id', 'DevToolsActivePort',
        'disconnected: not connected to DevTools',
        'Connection refused', 'NewConnectionError',
    ))


def _try_cookie_login(driver, account):
    """저장된 쿠키로 빠른 로그인 시도. 성공 시 True, Chrome 죽으면 None 반환."""
    if not account.cookie_data or not account.cookie_saved_at:
        return False
    if timezone.now() - account.cookie_saved_at > timedelta(hours=COOKIE_TTL_HOURS):
        return False

    try:
        driver.get('https://login.11st.co.kr')
        time.sleep(1)

        cookies = json.loads(account.cookie_data)
        for cookie in cookies:
            cookie.pop('sameSite', None)
            cookie.pop('expiry', None)
            try:
                driver.add_cookie(cookie)
            except Exception:
                pass

        driver.get('https://soffice.11st.co.kr/view/main')
        time.sleep(2)

        url = driver.current_url.lower()
        if 'login' in url or 'otploginform' in url or 'auth/front' in url:
            return False
        # /view/intro 는 '로그아웃 상태' 셀러오피스 랜딩(로그인/가입 안내 페이지)이다.
        # 쿠키가 만료되면 /view/main 이 여기로 리다이렉트되는데, 도메인은 여전히
        # soffice.11st.co.kr 이라 예전엔 '성공'으로 오판 → 풀로그인/OTP가 영영 안 돌고
        # 무효쿠키를 재저장하는 무한루프에 빠졌다. 실제 인증 마커(soContent)로 검증한다.
        if '/view/intro' in url:
            logger.info(f'[11st:{account.login_id}] 쿠키 만료(인트로 리다이렉트) → 풀로그인 필요')
            return False
        if 'soffice.11st.co.kr' in url and driver.find_elements(By.ID, 'soContent'):
            logger.info(f'[11st:{account.login_id}] 쿠키 로그인 성공')
            return True
        logger.info(f'[11st:{account.login_id}] 쿠키 로그인 미인증(soContent 없음, url={url[:60]}) → 풀로그인')
        return False
    except Exception as e:
        if _is_chrome_dead(e):
            logger.warning(f'[11st:{account.login_id}] 쿠키 로그인 중 Chrome 죽음: {e}')
            return None  # Chrome 재시작 필요 시그널
        logger.warning(f'[11st:{account.login_id}] 쿠키 로그인 오류: {e}')
        return False


def _save_cookies(driver, account):
    """현재 driver의 쿠키를 DB에 저장."""
    try:
        # login.11st.co.kr + soffice.11st.co.kr 양쪽 쿠키 모두 수집
        all_cookies = []
        try:
            all_cookies = driver.get_cookies()
        except Exception:
            pass
        if all_cookies:
            account.cookie_data = json.dumps(all_cookies)
            account.cookie_saved_at = timezone.now()
            account.save(update_fields=['cookie_data', 'cookie_saved_at'])
            logger.info(f'[11st:{account.login_id}] 쿠키 저장 ({len(all_cookies)}개)')
    except Exception as e:
        logger.warning(f'[11st:{account.login_id}] 쿠키 저장 실패: {e}')


def _drain_alerts(driver, max_loops=5, login_id=''):
    """발생한 alert 를 모두 자동 accept (login 단계별 잔여 모달 처리)."""
    n = 0
    for _ in range(max_loops):
        try:
            a = driver.switch_to.alert
            txt = a.text
            a.accept()
            n += 1
            logger.info(f'[11st:{login_id}] alert accept: {txt[:80]}')
            time.sleep(0.4)
        except Exception:
            break
    return n


def _dismiss_dom_modals(driver, login_id=''):
    """DOM 기반 팝업(.layer, .modal, .popup) 자동 닫기 — '닫기' '확인' '다음에' '나중에' 류 버튼 클릭."""
    closed = 0
    btn_xpaths = [
        '//button[contains(.,"다음에 변경") or contains(.,"다음에") or contains(.,"나중에")]',
        '//a[contains(.,"다음에 변경") or contains(.,"다음에") or contains(.,"나중에")]',
        '//button[normalize-space(text())="닫기" or normalize-space(text())="확인"]',
        '//a[contains(@class,"close") or contains(@class,"btn_close")]',
        '//button[contains(@class,"close") or contains(@class,"btn_close")]',
    ]
    for xp in btn_xpaths:
        try:
            els = driver.find_elements(By.XPATH, xp)
            for el in els:
                try:
                    if el.is_displayed():
                        driver.execute_script("arguments[0].click();", el)
                        closed += 1
                        time.sleep(0.4)
                except Exception:
                    pass
        except Exception:
            pass
    if closed:
        logger.info(f'[11st:{login_id}] DOM 모달 {closed}개 자동 닫기')
    return closed


# ── 오피스 현황 수집 (메인 페이지에서 14개 항목) ──
_OFFICE_XPATHS = {
    'cash':         '//*[@id="soContent"]/div[2]/div/div[4]/div[4]/div/div[2]/ul/li[1]/div[2]/a',
    'point':        '//*[@id="soContent"]/div[2]/div/div[4]/div[4]/div/div[2]/ul/li[2]/div[2]/a',
    'ad':           '//*[@id="soContent"]/div[2]/div/div[8]/div[2]/div/div[2]/div[2]/ul/li[1]/span[2]/a',
    'product_limit':'//*[@id="soContent"]/div[2]/div/div[8]/div[1]/div/div[2]/ul/li[5]/div/span[2]/a',
    'products':     '//*[@id="soContent"]/div[2]/div/div[8]/div[1]/div/div[2]/ul/li[1]/div/span[2]/a',
    'banned':       '//*[@id="soContent"]/div[2]/div/div[8]/div[1]/div/div[2]/ul/li[2]/div/span[2]/a',
    'overdue':      '//*[@id="soContent"]/div[2]/div/div[3]/div/div/div[2]/ul/li[3]/div[2]/a',
    'undelivered':  '//*[@id="soContent"]/div[2]/div/div[3]/div/div/div[2]/ul/li[4]/div[2]/a',
    'fulfillment':  '//*[@id="soContent"]/div[2]/div/div[4]/div[1]/div/ul[1]/li[1]/div[2]/span[1]',
    'shipping':     '//*[@id="soContent"]/div[2]/div/div[4]/div[1]/div/ul[1]/li[2]/div[2]/span[1]',
    'inquiry':      '//*[@id="soContent"]/div[2]/div/div[4]/div[1]/div/ul[1]/li[3]/div[2]/span[1]',
    # 퍼센트 (전체 li 텍스트에서 정규식 추출 — span 구조 변동 대비)
    'fulfillment_li': '//*[@id="soContent"]/div[2]/div/div[4]/div[1]/div/ul[1]/li[1]',
    'shipping_li':    '//*[@id="soContent"]/div[2]/div/div[4]/div[1]/div/ul[1]/li[2]',
    'inquiry_li':     '//*[@id="soContent"]/div[2]/div/div[4]/div[1]/div/ul[1]/li[3]',
}


def _get_text(driver, xpath, timeout=2.5):
    # 존재하면 즉시 반환(0 대기), 없으면 짧게만 대기 — 미발견 항목 헛대기 최소화.
    els = driver.find_elements(By.XPATH, xpath)
    if els:
        return (els[0].text or '').strip()
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        return (el.text or '').strip()
    except Exception:
        return ''


def _parse_int_safe(text):
    if not text:
        return 0
    try:
        return int(''.join(c for c in str(text) if c.isdigit()))
    except Exception:
        return 0


def _collect_office(driver, login_id):
    """로그인된 상태에서 메인 페이지 → 14개 항목 수집"""
    data = {k: 0 for k in (
        'cash', 'point', 'ad_balance', 'product_limit', 'products', 'banned',
        'available', 'overdue', 'undelivered', 'draft',
    )}
    data['fulfillment'] = data['shipping'] = data['inquiry'] = ''

    driver.get('https://soffice.11st.co.kr/view/main')
    # 컨테이너 로드 1회 확인(최대 10s) — 이후 항목 조회는 짧은 대기로 충분(헛대기 방지)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'soContent'))
        )
    except Exception:
        pass
    time.sleep(1.5)

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.7);")
    time.sleep(1)

    data['cash'] = _parse_int_safe(_get_text(driver, _OFFICE_XPATHS['cash']))
    data['point'] = _parse_int_safe(_get_text(driver, _OFFICE_XPATHS['point']))
    data['ad_balance'] = _parse_int_safe(_get_text(driver, _OFFICE_XPATHS['ad']))

    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)

    data['product_limit'] = _parse_int_safe(_get_text(driver, _OFFICE_XPATHS['product_limit']))
    data['products'] = _parse_int_safe(_get_text(driver, _OFFICE_XPATHS['products']))
    data['banned'] = _parse_int_safe(_get_text(driver, _OFFICE_XPATHS['banned']))
    data['available'] = max(data['product_limit'] - data['products'], 0)
    data['overdue'] = _parse_int_safe(_get_text(driver, _OFFICE_XPATHS['overdue']))
    data['undelivered'] = _parse_int_safe(_get_text(driver, _OFFICE_XPATHS['undelivered']))
    # 평점 + 퍼센트 합쳐 저장 ("우수 97.3%")
    import re as _re_pct
    def _rate_pct(key):
        rate = _get_text(driver, _OFFICE_XPATHS[key]).strip()
        pct = ''
        m = _re_pct.search(r'(\d+\.?\d*)\s*%', _get_text(driver, _OFFICE_XPATHS.get(key + '_li', ''), timeout=3))
        if m:
            pct = m.group(1) + '%'
        return (f'{rate} {pct}'.strip())[:50]
    data['fulfillment'] = _rate_pct('fulfillment')
    data['shipping'] = _rate_pct('shipping')
    data['inquiry'] = _rate_pct('inquiry')

    return data


def _do_login(driver, login_id, password):
    driver.get(LOGIN_URL)
    time.sleep(3)
    # 페이지 진입 직후 alert/모달 자동 해제 (단, OTP 단계면 '확인' 오클릭 방지 위해 모달닫기 생략)
    _drain_alerts(driver, login_id=login_id)
    if 'otpLoginForm' not in driver.current_url:
        _dismiss_dom_modals(driver, login_id=login_id)

    try:
        # 쿠키 부분인증 등으로 이미 OTP 단계(otpLoginForm)면 아이디/비번 생략 → 바로 OTP 진행
        if 'otpLoginForm' not in driver.current_url:
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
        else:
            logger.info(f'[11st:{login_id}] 이미 OTP 단계(쿠키 부분인증) → 아이디/비번 생략')

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

        # 비밀번호 변경 캠페인 페이지 자동 우회 (#nextTime "다음에 변경")
        if 'passwordCampaign' in driver.current_url:
            logger.info(f'[11st:{login_id}] 비번 캠페인 페이지 → "다음에 변경" 클릭')
            try:
                next_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.ID, 'nextTime'))
                )
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(3)
                # alert 가능
                try:
                    a = driver.switch_to.alert
                    logger.info(f'[11st:{login_id}] campaign alert: {a.text}')
                    a.accept()
                    time.sleep(2)
                except Exception:
                    pass
                logger.info(f'[11st:{login_id}] 캠페인 우회 후 URL: {driver.current_url}')
            except Exception as e:
                logger.warning(f'[11st:{login_id}] #nextTime 클릭 실패: {e}')

        # 제출 후 OTP 페이지/셀러오피스 리다이렉트를 충분히 대기 (느린 리다이렉트 시 조기 강제이동 방지)
        for _ in range(15):
            _cu = driver.current_url
            if 'otpLoginForm' in _cu or 'soffice.11st.co.kr' in _cu:
                break
            time.sleep(1)

        # 캠페인 우회 후 셀러오피스에 도달 못 했으면 직접 진입
        if 'soffice.11st.co.kr' not in driver.current_url and 'otpLoginForm' not in driver.current_url:
            try:
                driver.get('https://soffice.11st.co.kr/view/main')
                time.sleep(3)
            except Exception:
                pass

        # OTP 체크
        if 'otpLoginForm' in driver.current_url:
            logger.info(f'[11st:{login_id}] OTP 인증 페이지 도달')
            # 디버그용 페이지 캡처
            try:
                dbg_dir = Path('/tmp/avengers_otp_debug')
                dbg_dir.mkdir(exist_ok=True)
                ts = int(time.time())
                driver.save_screenshot(str(dbg_dir / f'{login_id}_{ts}.png'))
                (dbg_dir / f'{login_id}_{ts}.html').write_text(driver.page_source, encoding='utf-8')
            except Exception:
                pass

            # 11번가 OTP 페이지 정확한 흐름:
            # 1) auth_type_01 (KAKAO) 라디오 선택 (default)
            # 2) "인증번호 전송" 버튼 클릭 (onclick=requestOTP)
            # 3) 카카오톡 발송 → 폰에서 받음 (또는 SMS 폴백)
            # 4) auth_num_kakao 입력란에 6자리 입력
            # 5) "확인" 버튼 클릭 (onclick=login)
            try:
                # 1) KAKAO 라디오 명시적 클릭 (이미 checked지만 보장)
                try:
                    radio = driver.find_element(By.ID, 'auth_type_01')
                    if not radio.is_selected():
                        driver.execute_script("arguments[0].click();", radio)
                except Exception:
                    pass

                # 2) "인증번호 전송" 버튼 (cell 타입, requestOTP onclick)
                send_btn_xpaths = [
                    "//button[@onclick='requestOTP();' and contains(@data-log-body, 'cell') and not(@id)]",
                    "//button[@onclick='requestOTP();' and contains(@data-log-actionid-label,'certification_num') and contains(@data-log-body,'cell')]",
                    "//button[normalize-space(text())='인증번호 전송' and contains(@data-log-body,'cell')]",
                ]
                otp_since_ms = int(time.time() * 1000) - 8000   # 전송 직전(8초 여유) 이후 OTP만 인정
                send_clicked = False
                for sel in send_btn_xpaths:
                    try:
                        btn = driver.find_element(By.XPATH, sel)
                        driver.execute_script("arguments[0].click();", btn)
                        send_clicked = True
                        logger.info(f'[11st:{login_id}] "인증번호 전송" 클릭')
                        break
                    except Exception:
                        continue
                if not send_clicked:
                    logger.error(f'[11st:{login_id}] "인증번호 전송" 버튼 못 찾음')
                    return False

                # alert 처리
                time.sleep(1.5)
                try:
                    alert = driver.switch_to.alert
                    logger.info(f'[11st:{login_id}] alert: {alert.text}')
                    alert.accept()
                except Exception:
                    pass
            except Exception as e:
                logger.error(f'[11st:{login_id}] OTP 발송 단계 오류: {e}')
                return False

            # 3) OTP 대기 — DB(smsApp 네트워크 푸시) 우선, USB 없이도 인증 가능
            logger.info(f'[11st:{login_id}] OTP 대기 (DB+adb 병행, 최대 180초)...')
            otp_code = _wait_for_otp_any(otp_since_ms, timeout=180)
            if not otp_code:
                logger.warning(f'[11st:{login_id}] OTP 미수신 timeout')
                return False

            logger.info(f'[11st:{login_id}] OTP 코드 수신: {otp_code}')

            # 4) 입력란 (auth_num_kakao)
            try:
                otp_input = driver.find_element(By.ID, 'auth_num_kakao')
                otp_input.clear()
                otp_input.send_keys(otp_code)
                logger.info(f'[11st:{login_id}] OTP 입력 OK')
            except Exception as e:
                logger.error(f'[11st:{login_id}] 입력란 못 찾음: {e}')
                return False

            # 5) "확인" 버튼 (onclick=login(), cell 타입)
            confirm_xpaths = [
                "//button[@onclick='login();' and contains(@data-log-body,'cell')]",
                "//button[@onclick='login();' and contains(@data-log-actionid-label,'confirm') and contains(@data-log-body,'cell')]",
            ]
            confirmed = False
            for sel in confirm_xpaths:
                try:
                    btn = driver.find_element(By.XPATH, sel)
                    driver.execute_script("arguments[0].click();", btn)
                    confirmed = True
                    logger.info(f'[11st:{login_id}] "확인" 클릭')
                    break
                except Exception:
                    continue
            if not confirmed:
                logger.error(f'[11st:{login_id}] 확인 버튼 못 찾음')
                return False

            time.sleep(4)
            try:
                alert = driver.switch_to.alert
                logger.info(f'[11st:{login_id}] confirm alert: {alert.text}')
                alert.accept()
                time.sleep(2)
            except Exception:
                pass

            logger.info(f'[11st:{login_id}] OTP 후 URL: {driver.current_url}')
            if 'soffice.11st.co.kr' in driver.current_url or 'selleroffice' in driver.current_url:
                logger.info(f'[11st:{login_id}] OTP 인증 성공!')
                try:
                    from apps.cpc.models import CrawlerAccount
                    CrawlerAccount.objects.filter(login_id=login_id, platform='11st').update(last_otp_at=timezone.now())
                except Exception:
                    pass
                return True
            logger.warning(f'[11st:{login_id}] OTP 후 예상 페이지 아님: {driver.current_url}')
            return False

        # 로그인 성공 확인
        if 'soffice.11st.co.kr' in driver.current_url or 'selleroffice' in driver.current_url:
            return True

        return False
    except Exception as e:
        logger.error(f'[{login_id}] 로그인 실패: {e}')
        return False


def _download_cost_xls(driver, download_dir, login_id, cost_type='sellerpoint', start_date=None, end_date=None):
    # CDP 명령으로 다운로드 경로 설정
    driver.execute_cdp_cmd('Page.setDownloadBehavior', {
        'behavior': 'allow', 'downloadPath': str(download_dir)
    })

    cost_url = COST_URL_SELLERCASH if cost_type == 'sellercash' else COST_URL_SELLERPOINT
    iframe_id = '8301' if cost_type == 'sellercash' else '8201'
    driver.get(cost_url)
    time.sleep(3)

    try:
        # iframe 전환 (11번가 soffice 응답 지연 대비 30초로 여유)
        iframe = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, f"//iframe[contains(@id,'{iframe_id}')]"))
        )
        driver.switch_to.frame(iframe)
        time.sleep(2)

        if start_date and end_date:
            # 날짜 직접지정 (startDate/endDate 필드에 YYYY/MM/DD 입력)
            for nm, val in [('startDate', start_date), ('endDate', end_date),
                            ('initStartDate', start_date), ('initEndDate', end_date)]:
                try:
                    driver.execute_script(
                        "var els=document.getElementsByName(arguments[0]); if(els.length){els[0].value=arguments[1];}",
                        nm, val)
                except Exception:
                    pass
        else:
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

        # ChromeDriver idle timeout 방지: 즉시 빈 페이지로 이동
        try:
            driver.get('about:blank')
        except Exception:
            pass

        return filepath
    except Exception as e:
        # TimeoutException 등은 message가 비어 있어 원인이 안 보임 → 예외 타입명을 함께 남김
        logger.error(f'[{login_id}] 다운로드 실패({cost_type}): {type(e).__name__}: {str(e).splitlines()[0] if str(e).strip() else "(no message)"}')
        try:
            driver.switch_to.default_content()
        except Exception:
            pass
        return None


def _parse_cost_rows(filepath, cost_type='sellerpoint'):
    """광고비 XLS를 파싱해 거래 튜플 목록 반환 (seq 미부여 — 저장 시 합쳐서 부여).
    반환: [(dt_aware, tx_type, desc, amount, balance), ...]"""
    filepath = str(filepath)
    rows = []
    try:
        if os.path.getsize(filepath) == 0:
            # 11번가는 해당 기간 거래내역이 없으면 0바이트 파일을 내려준다 — 실패 아님
            logger.info(f'광고비 파일 비어있음(데이터 없음): {os.path.basename(filepath)}')
            return []
    except OSError:
        pass
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
        return []
    if not rows:
        return []

    header_idx = None
    for i, row in enumerate(rows):
        row_str = ' '.join(str(c or '') for c in row)
        if '거래일시' in row_str or '거래항목' in row_str:
            header_idx = i
            break
    if header_idx is None:
        header_idx = 5 if cost_type == 'sellercash' else 1

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

    items = []
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
            dt_aware = timezone.make_aware(dt) if timezone.is_naive(dt) else dt
            items.append((dt_aware, classify_11st_description(desc), desc[:255], amount, balance))
        except Exception as e:
            logger.warning(f'행 파싱 오류: {e}')
            continue
    return items


def _save_cost_rows(seller_id, items):
    """거래 튜플 목록을 DB에 통째로 교체 저장 (양쪽 결제수단 합친 뒤 호출).
    같은 거래시각엔 순번 seq를 매겨 같은 초 다중거래 보존, 재크롤 시 중복/누락 0."""
    from apps.cpc.models import ElevenCostHistory
    from django.db import transaction as _txn
    if not items:
        return 0
    seq_by_dt = {}
    instances = []
    for dt_aware, ttype, desc, amount, balance in items:
        seq = seq_by_dt.get(dt_aware, 0)
        seq_by_dt[dt_aware] = seq + 1
        instances.append(ElevenCostHistory(
            seller_id=seller_id, transaction_datetime=dt_aware, seq=seq,
            transaction_type=ttype, raw_description=desc, amount=amount, balance=balance))
    dts = [i.transaction_datetime for i in instances]
    lo, hi = min(dts), max(dts)
    with _txn.atomic():
        ElevenCostHistory.objects.filter(
            seller_id=seller_id, transaction_datetime__gte=lo, transaction_datetime__lte=hi).delete()
        ElevenCostHistory.objects.bulk_create(instances, batch_size=1000)
    return len(instances)


def _parse_and_save_xls(filepath, seller_id, cost_type='sellerpoint'):
    """단일 파일 파싱+저장 (호환용)."""
    return _save_cost_rows(seller_id, _parse_cost_rows(filepath, cost_type))


def _tg_split_send(cfg, recipients, header_lines, body_lines, max_chars=3500, max_lines=25):
    """헤더 + 본문 라인을 텔레그램 메시지 길이 한도에 맞춰 여러 개로 분할 발송.
    문자가 잘리지 않도록 max_chars(기본 3500, 텔레그램 한도 4096보다 보수적) 또는
    max_lines(메시지당 본문 줄수) 중 먼저 도달하는 기준으로 나눔 → 항상 2~3개로 분할.
    각 메시지에 (i/n) 표시."""
    import urllib.request
    chunks = []
    cur = list(header_lines)
    cur_len = sum(len(l) + 1 for l in cur)
    body_in_cur = 0
    for line in body_lines:
        if cur and (cur_len + len(line) + 1 > max_chars or body_in_cur >= max_lines):
            chunks.append(cur)
            cur = []
            cur_len = 0
            body_in_cur = 0
        cur.append(line)
        cur_len += len(line) + 1
        body_in_cur += 1
    if cur:
        chunks.append(cur)

    n = len(chunks)
    for i, ch in enumerate(chunks, 1):
        prefix = f'({i}/{n})\n' if n > 1 else ''
        text = prefix + '\n'.join(ch)
        for r in recipients:
            try:
                data = json.dumps({'chat_id': r.chat_id, 'text': text}).encode()
                req = urllib.request.Request(
                    f'https://api.telegram.org/bot{cfg.bot_token}/sendMessage',
                    data=data, headers={'Content-Type': 'application/json'})
                urllib.request.urlopen(req, timeout=10)
            except Exception as e:
                logger.warning(f'텔레그램 발송 실패 ({r.chat_id}): {e}')
        time.sleep(0.4)
    return n


def _send_telegram_report(collected, failed, accounts):
    """11번가 당일 광고비를 '계정별 광고비'만 텔레그램 발송 (2~3개 분할).
    - 전체 활성 api 계정 기준으로 집계 → 부분 크롤이어도 합계가 대시보드와 일치
    - 합계는 표시된 계정별 광고비의 정확한 합 (불일치 없음)"""
    from apps.cpc.models import TelegramConfig, TelegramRecipient, ElevenCostHistory, CrawlerAccount
    from django.db.models import Sum

    cfg = TelegramConfig.objects.first()
    if not cfg or not cfg.bot_token:
        return
    recipients = list(TelegramRecipient.objects.filter(is_active=True))
    if not recipients:
        return

    import pytz
    from datetime import datetime, timedelta
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst)
    today = now.date()
    start = kst.localize(datetime.combine(today, datetime.min.time()))
    end = start + timedelta(days=1)

    # 전체 활성 11번가 api 계정 기준 (이번 크롤 대상에 한정하지 않음 → 대시보드 합계와 일치)
    all_accts = CrawlerAccount.objects.filter(platform='11st', is_active=True).exclude(api_key='')
    rows = []
    total_cpc = 0
    zero_n = 0
    for acct in all_accts:
        cpc = abs(ElevenCostHistory.objects.filter(
            seller_id=acct.login_id, transaction_type='CPC',
            transaction_datetime__gte=start, transaction_datetime__lt=end
        ).aggregate(t=Sum('amount'))['t'] or 0)
        total_cpc += cpc
        if cpc > 0:
            rows.append((acct.seller_name or acct.login_id, cpc))
        else:
            zero_n += 1
    rows.sort(key=lambda r: r[1], reverse=True)

    seller_lines = [f'{name}: {cpc:,}원' for name, cpc in rows]
    header = [
        f'📊 11번가 당일 광고비 ({now.strftime("%m/%d %H:%M")})',
        f'💰 합계 {total_cpc:,}원  (발생 {len(rows)}개 / 0원 {zero_n}개)',
        '',
    ]
    _tg_split_send(cfg, recipients, header, seller_lines)


def _alert_evening_cpc(after_hour=17):
    """크롤 후, 오늘 {after_hour}시 이후 누적 발생한 CPC(광고비)를 계정별로 텔레그램 알림.
    {after_hour}시 이후 실행에서만 동작하고, 광고비가 발생한 계정만(어떤 계정·얼마) 보고한다."""
    from apps.cpc.models import TelegramConfig, TelegramRecipient, ElevenCostHistory, CrawlerAccount
    from django.db.models import Sum, Count
    import pytz
    from datetime import datetime, timedelta
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst)
    if now.hour < after_hour:
        return False    # 17시 이전 실행(11·15시)은 알림 안 함
    cfg = TelegramConfig.objects.first()
    if not cfg or not cfg.bot_token:
        return False
    recipients = list(TelegramRecipient.objects.filter(is_active=True))
    if not recipients:
        return False
    midnight = kst.localize(datetime.combine(now.date(), datetime.min.time()))
    start = midnight + timedelta(hours=after_hour)   # 오늘 17:00 (KST)
    end = midnight + timedelta(days=1)               # 내일 00:00
    name_by_id = {a.login_id: (a.seller_name or a.login_id)
                  for a in CrawlerAccount.objects.filter(platform='11st')}
    agg = (ElevenCostHistory.objects
           .filter(transaction_type='CPC', transaction_datetime__gte=start, transaction_datetime__lt=end)
           .values('seller_id').annotate(t=Sum('amount'), n=Count('id')))
    rows = []
    for r in agg:
        cpc = abs(r['t'] or 0)
        if cpc > 0:
            rows.append((name_by_id.get(r['seller_id'], r['seller_id']), cpc, r['n']))
    if not rows:
        return False    # 17시 이후 발생 광고비 없음 → 알림 보내지 않음
    rows.sort(key=lambda x: x[1], reverse=True)
    total = sum(c for _, c, _ in rows)
    header = [
        f'📢 11번가 {after_hour}시 이후 광고비 발생 ({now.strftime("%m/%d %H:%M")} 기준)',
        f'💰 누적 {total:,}원 · {len(rows)}개 계정',
        '',
    ]
    body = [f'{name}: {cpc:,}원 ({n}건)' for name, cpc, n in rows]
    _tg_split_send(cfg, recipients, header, body)
    return True


def run_all_accounts(log_fn=None, account_filter=None, force=False, start_date=None, scheduled=False):
    import random
    # 외부 지정 시작일(YYYY-MM-DD 또는 YYYY/MM/DD) → 'YYYY/MM/DD'로 정규화
    override_start = None
    if start_date:
        override_start = str(start_date).strip().replace('-', '/')
    from apps.cpc.models import CrawlerAccount, CrawlerLog
    from apps.cpc import eleven_block_guard as guard

    # 사전점검: 차단/접속불가/다른 크롤 동시실행 금지 (전역 단일 크롤 — IP 차단 방지)
    _pf_ok, _pf_reason = guard.preflight('광고비', wait=scheduled)
    if not _pf_ok:
        msg = f'⏭️ 광고비 크롤 건너뜀 — {_pf_reason}'
        if log_fn:
            log_fn(msg)
        if scheduled:
            guard.notify_problem('11번가광고비', f'예약 크롤 미실행 — {_pf_reason}')
        return {'collected': 0, 'failed': 0, 'skipped': _pf_reason}

    # 활성 + 차단되지 않은 계정
    accounts = list(
        CrawlerAccount.objects.filter(platform='11st', is_active=True)
        .exclude(crawling_status__in=['차단됨', '실패'])
    )
    if account_filter:
        # 명시 지정 시 정확히 그 계정만 (api_key 없어도 크롤 — 예: 정지계정 과거자료 수집)
        accounts = [a for a in accounts if a.login_id in account_filter]
    # else: 활성 11번가 전체 (api 없는 대기계정도 자동 스케줄에 포함) — accounts 그대로 사용

    # 크롤 순서: 1>2>3>4등급 → 광고비이력 보유 → 나머지 (등급 높은 계정 우선 수집)
    if accounts:
        from apps.cpc.models import ElevenSellerGrade, ElevenCostHistory
        from django.db.models import Max as _Max
        _ids = [a.login_id for a in accounts]
        _gids = list(ElevenSellerGrade.objects.filter(eleven_id__in=_ids)
                     .values('eleven_id').annotate(mx=_Max('id')).values_list('mx', flat=True))
        _grade = {g.eleven_id: g.grade for g in ElevenSellerGrade.objects.filter(id__in=_gids) if g.grade}
        _adset = set(ElevenCostHistory.objects.filter(seller_id__in=_ids)
                     .values_list('seller_id', flat=True).distinct())

        def _crawl_rank(a):
            g = _grade.get(a.login_id)
            if g in (1, 2, 3, 4):
                tier = g
            elif a.login_id in _adset:
                tier = 5          # 1~4등급 아님 + 광고비 이력 있음
            else:
                tier = 6          # 나머지
            return (tier, g or 99, a.display_order or 0, a.login_id)

        accounts.sort(key=_crawl_rank)

    if not accounts:
        msg = '활성 11번가 계정이 없습니다.'
        if log_fn:
            log_fn(msg)
        guard.release_global_lock()
        return {'collected': 0, 'failed': 0}

    # 차단 회피 보수적 페이싱
    INTER_ACCOUNT_SLEEP = (5.0, 10.0)          # 5~10초 (ChromeDriver 146 idle timeout 회피)
    CIRCUIT_BREAKER_THRESHOLD = 5             # 연속 5회 차단신호 시 글로벌 락 + 중단
    SKIP_RECENT_HOURS = 6                     # 6시간 내 성공 계정 스킵
    MAX_CONNECT_ATTEMPTS = 3                  # 계정당 접속(로그인) 최대 3회 시도, 3회 실패 시 중지→다음 계정
    COST_DL_RETRIES = 2                       # 광고비 XLS 다운로드 결제수단별 시도 횟수(일시적 iframe/클릭 실패 복구)

    # 신선도 필터 — 최근 성공한 계정 제외 (force=True 면 무시하고 전체 재수집)
    accounts_filtered = []
    skipped_recent = []
    for a in accounts:
        if (not force) and guard.is_recently_synced(a.last_crawled_at, hours=SKIP_RECENT_HOURS) and a.crawling_status == '정상':
            skipped_recent.append(a.login_id)
        else:
            accounts_filtered.append(a)
    accounts = accounts_filtered
    total_accounts = len(accounts)
    if log_fn and skipped_recent:
        log_fn(f'[cost] 최근 {SKIP_RECENT_HOURS}h 내 성공 {len(skipped_recent)}계정 스킵, 대상 {total_accounts}계정')

    collected, failed = 0, 0
    driver = None
    accounts_since_restart = 0
    DRIVER_RESTART_EVERY = 1  # 매 계정마다 driver 새로 생성 (Chrome 146 안정성)

    def _safe_quit(d):
        if not d:
            return
        try:
            d.quit()
        except Exception:
            pass

    def _new_driver(kill_existing=True):
        d = create_driver(kill_existing=kill_existing)
        # 암묵적 대기(implicitly_wait)를 0으로 끈다. browser.py는 기본 10초를 거는데,
        # 이 크롤러는 전부 명시적 WebDriverWait/짧은 폴링(_get_text 2.5초)에 의존한다.
        # 암묵 10초가 섞이면 미발견 요소마다 find_elements가 10초씩 헛대기 →
        # 오피스 수집(_get_text ~19회)이 계정당 수 분 hang, 다운로드 iframe 대기도 부풀어
        # 대량 '다운로드 실패'를 유발한다. (eleven_loss_delete 와 동일한 처방)
        try:
            d.implicitly_wait(0)
        except Exception:
            pass
        return d

    def _is_dead_driver_error(e):
        s = str(e)
        return any(k in s for k in ('Connection refused', 'NewConnectionError',
                                      'invalid session id', 'chrome not reachable',
                                      'session deleted', 'disconnected'))

    consecutive_block_signals = 0
    consecutive_login_failures = 0
    LOGIN_FAIL_ABORT_THRESHOLD = 5
    aborted_due_to_block = False

    try:
        driver = _new_driver()

        # 서버 접속 사전점검 (실패해도 계속 진행 — 첫 로그인에서 재확인)
        try:
            driver.get('https://login.11st.co.kr')
            time.sleep(3)
            url = driver.current_url.lower()
            if '11st.co.kr' not in url:
                logger.warning(f'[11st:사전점검] URL 이상: {url}')
        except Exception as e:
            logger.warning(f'[11st:사전점검] 접속 테스트 실패 (계속 진행): {e}')
            _safe_quit(driver)
            driver = _new_driver()

        if False:  # 서버 체크로 전면 중단하지 않음
            msg = '⛔ 11번가 서버 접속 불가 — 크롤링 전면 중단 (로그인 시도 안 함)'
            logger.error(msg)
            if log_fn: log_fn(msg)
            CrawlerLog.objects.create(
                platform='11st', level='error',
                message=msg, account_id='SYSTEM'
            )
            guard.set_blocked(30, '11번가 서버 접속 불가')
            _safe_quit(driver)
            stop_display()
            guard.release_global_lock()
            return {'collected': 0, 'failed': 0, 'aborted_due_to_block': True, 'server_unreachable': True}

        for idx, account in enumerate(accounts, 1):
            # 매 계정 시작 전 글로벌 락 재확인
            if guard.guard_and_skip(f'cost[{account.login_id}]'):
                aborted_due_to_block = True
                break

            if account.crawling_status in ('차단됨', '실패'):
                if log_fn: log_fn(f'[11st:{account.login_id}] {account.crawling_status} - 건너뜀')
                continue

            login_id = account.login_id

            def log(msg):
                logger.info(f'[11st:{login_id}] {msg}')
                if log_fn:
                    log_fn(f'[11st:{login_id}] {msg}')

            # 연속 로그인 실패 3회 시 즉시 중단 (서버 문제로 판단)
            if consecutive_login_failures >= LOGIN_FAIL_ABORT_THRESHOLD:
                msg = f'⛔ 연속 {LOGIN_FAIL_ABORT_THRESHOLD}회 로그인 실패 — 서버 문제 의심, 크롤링 중단'
                logger.error(msg)
                if log_fn: log_fn(msg)
                CrawlerLog.objects.create(
                    platform='11st', level='error',
                    message=msg, account_id='SYSTEM'
                )
                guard.set_blocked(30, f'연속 {LOGIN_FAIL_ABORT_THRESHOLD}회 로그인 실패')
                aborted_due_to_block = True
                break

            # 매 N개 계정마다 preventive 재생성
            if accounts_since_restart >= DRIVER_RESTART_EVERY:
                log(f'driver 재시작')
                _safe_quit(driver)
                time.sleep(1)
                driver = _new_driver(kill_existing=False)
                accounts_since_restart = 0

            # ════════════════════════════════════════════════════════════
            # 접속(로그인) 단계 — 계정당 최대 MAX_CONNECT_ATTEMPTS(3)회 시도.
            # 3회 모두 실패하면 반드시 중지하고 '실패' 표시 후 다음 계정으로.
            # (반복 로그인으로 인한 11번가 차단 방지)
            # ════════════════════════════════════════════════════════════
            logged_in = False
            used_cookie = False
            for attempt in range(1, MAX_CONNECT_ATTEMPTS + 1):
                # 시도 사이 글로벌 차단 락 재확인
                if guard.guard_and_skip(f'cost[{login_id}] 접속'):
                    aborted_due_to_block = True
                    break
                try:
                    # driver 생존 확인 — 죽었으면 재생성
                    try:
                        _ = driver.current_url
                    except Exception:
                        log('driver 죽어있음 → 재생성')
                        _safe_quit(driver)
                        driver = _new_driver(kill_existing=True)
                        accounts_since_restart = 0

                    # 이전 세션 완전 정리
                    try:
                        driver.get('about:blank')
                        time.sleep(0.3)
                        driver.delete_all_cookies()
                    except Exception:
                        pass

                    # 1) 쿠키 로그인 우선 시도 (1회차에만) — USE_COOKIE_LOGIN=False면 건너뛰고 항상 풀로그인
                    if attempt == 1 and USE_COOKIE_LOGIN:
                        ck = _try_cookie_login(driver, account)
                        if ck is None:
                            log('Chrome 죽음 → driver 재생성')
                            _safe_quit(driver)
                            driver = _new_driver(kill_existing=True)
                            accounts_since_restart = 0
                            ck = False
                        if ck:
                            logged_in = True
                            used_cookie = True
                            break

                    # 2) 일반 로그인
                    try:
                        driver.get('https://login.11st.co.kr/auth/front/logout.tmall')
                        time.sleep(0.5)
                    except Exception:
                        pass
                    try:
                        driver.get('about:blank')
                        time.sleep(0.3)
                        driver.delete_all_cookies()
                    except Exception:
                        pass

                    log(f'로그인 시도 {attempt}/{MAX_CONNECT_ATTEMPTS}...')
                    if _do_login(driver, login_id, account.password_enc):
                        logged_in = True
                        break
                    raise Exception('로그인 실패')

                except Exception as le:
                    log(f'접속 실패 {attempt}/{MAX_CONNECT_ATTEMPTS}: {str(le)[:120]}')
                    # 차단 신호면 글로벌 circuit breaker 누적
                    if guard.is_block_signal(le):
                        consecutive_block_signals += 1
                        if consecutive_block_signals >= CIRCUIT_BREAKER_THRESHOLD:
                            guard.report_signal(le, source='cost crawler')
                            aborted_due_to_block = True
                            log('⛔ circuit breaker 발동 — 글로벌 차단 락, 즉시 중단')
                            break
                    # driver 죽었으면 재생성
                    if _is_dead_driver_error(le):
                        _safe_quit(driver)
                        try:
                            driver = _new_driver(kill_existing=True)
                            accounts_since_restart = 0
                        except Exception:
                            pass
                    # 마지막 시도가 아니면 잠시 대기 후 재시도
                    if attempt < MAX_CONNECT_ATTEMPTS:
                        time.sleep(random.uniform(2.0, 4.0))

            if aborted_due_to_block:
                break

            if not logged_in:
                # ── 접속 3회 실패 → 반드시 중지하고 다음 계정으로 ──
                consecutive_login_failures += 1
                account.fail_count += 1
                account.mark_connect_failed()  # connect_fail_count++ , 3회 도달 시 '실패'
                if account.fail_count >= 30 and account.crawling_status != '실패':
                    account.crawling_status = '차단됨'
                account.save()
                failed += 1
                err_msg = f'접속 {MAX_CONNECT_ATTEMPTS}회 실패 → 중지(다음 계정), 상태={account.crawling_status}'
                CrawlerLog.objects.create(
                    platform='11st', level='error', message=err_msg, account_id=login_id)
                log(f'⛔ {err_msg}')
                # 문제 발생 알림 — 텔레그램
                try:
                    guard._send_telegram_alert(
                        f'⚠️ [11번가 접속실패]\n계정: {login_id} ({account.seller_name})\n'
                        f'접속 {MAX_CONNECT_ATTEMPTS}회 연속 실패 → 중지하고 다음 계정으로 진행.\n'
                        f'상태: {account.crawling_status}')
                except Exception:
                    pass
                # 다음 계정 전 대기
                if idx < total_accounts:
                    time.sleep(random.uniform(*INTER_ACCOUNT_SLEEP))
                continue

            # ── 접속 성공 ──
            consecutive_login_failures = 0
            consecutive_block_signals = 0
            account.reset_connect_fail()
            if used_cookie:
                log('쿠키 재사용 (로그인 우회)')
            else:
                log('로그인 성공')
            # 성공한 쿠키를 항상 재저장 → cookie_saved_at 갱신(롤포워드)로 OTP 빈도 최소화
            _save_cookies(driver, account)
            accounts_since_restart += 1

            try:
                # ── 1) 오피스 현황 수집 (메인 페이지) ──
                office_ok = False
                try:
                    office_data = _collect_office(driver, login_id)
                    from apps.cpc.models import ElevenSellerOfficeStat
                    ElevenSellerOfficeStat.objects.create(account=account, **office_data)
                    log(f'오피스: 캐시={office_data["cash"]:,} 포인트={office_data["point"]:,} 상품={office_data["products"]:,}')
                    office_ok = True
                except Exception as oe:
                    log(f'오피스 수집 실패 (광고비는 계속): {oe}')

                # ── 2) 광고비 XLS 다운로드 (셀러포인트+셀러캐시 모두, 전월1일~오늘) ──
                dl_dir = DOWNLOAD_BASE / login_id
                dl_dir.mkdir(parents=True, exist_ok=True)

                _now = timezone.localtime()
                end_date = _now.strftime('%Y/%m/%d')
                if override_start:
                    start_date = override_start            # 외부 지정 시작일 (예: 2026/01/01)
                else:
                    _pm = _now.month - 1 or 12
                    _py = _now.year if _now.month > 1 else _now.year - 1
                    start_date = f'{_py}/{_pm:02d}/01'   # 전월 1일

                items = []
                got_types = {}
                for ct in ('sellerpoint', 'sellercash'):
                    d2 = dl_dir / ct
                    d2.mkdir(parents=True, exist_ok=True)
                    fp = None
                    for dl_try in range(1, COST_DL_RETRIES + 1):
                        for f in d2.iterdir():
                            f.unlink(missing_ok=True)
                        suffix = f' [재시도 {dl_try}/{COST_DL_RETRIES}]' if dl_try > 1 else ''
                        log(f'광고비 다운로드... ({ct} {start_date}~{end_date}){suffix}')
                        fp = _download_cost_xls(driver, str(d2), login_id, cost_type=ct,
                                                start_date=start_date, end_date=end_date)
                        if fp:
                            break
                        if dl_try < COST_DL_RETRIES:
                            time.sleep(random.uniform(2.0, 4.0))
                    if fp:
                        got_types[ct] = True
                        before = len(items)
                        items += _parse_cost_rows(fp, ct)
                        log(f'  {ct}: {len(items) - before}건')
                    else:
                        got_types[ct] = False
                        log(f'  {ct}: 다운로드 실패')

                # 양쪽(셀러포인트+셀러캐시) 모두 받아야 저장. 한쪽만 받으면 통째교체로
                # 반대편 결제수단 데이터가 같은 기간에서 삭제·미복원되어 유실되므로 실패 처리(다음 회차 재수집).
                if got_types.get('sellerpoint') and got_types.get('sellercash'):
                    saved = _save_cost_rows(login_id, items)   # 양쪽 합쳐 통째로 교체 저장
                    log(f'{saved}건 저장 완료 (셀러포인트+셀러캐시 합산)')
                    account.crawling_status = '정상'
                    account.last_crawled_at = timezone.now()
                    try: account.refresh_from_db(fields=['last_otp_at'])  # _do_login이 기록한 OTP시각 보존
                    except Exception: pass
                    account.save()
                    collected += 1
                    msg = f'{saved}건 저장'
                    if office_ok:
                        msg += ' + 오피스OK'
                    CrawlerLog.objects.create(
                        platform='11st', level='success', message=msg, account_id=login_id)
                    guard.notify_success(login_id, 'cost')   # 연속실패 카운터 리셋
                else:
                    _failed_ct = [c for c in ('sellerpoint', 'sellercash') if not got_types.get(c)]
                    raise Exception(f'다운로드 실패 ({", ".join(_failed_ct)})')

            except Exception as e:
                # 데이터 수집 단계 실패 (접속은 성공 → connect_fail 로 세지 않음)
                account.fail_count += 1
                if account.fail_count >= 30:
                    account.crawling_status = '차단됨'
                try: account.refresh_from_db(fields=['last_otp_at'])
                except Exception: pass
                account.save()
                failed += 1

                CrawlerLog.objects.create(
                    platform='11st', level='error',
                    message=str(e),
                    account_id=login_id
                )
                log(f'수집 실패: {e}')
                try:
                    # 일시적 실패는 보류, 연속 실패(회복 안 됨)만 알림 (1일 1회)
                    guard.notify_failure(login_id, 'cost', e, account.seller_name)
                except Exception:
                    pass

                # 차단 신호 탐지 — circuit breaker
                if guard.is_block_signal(e):
                    consecutive_block_signals += 1
                    log(f'차단신호 감지 ({consecutive_block_signals}/{CIRCUIT_BREAKER_THRESHOLD})')
                    if consecutive_block_signals >= CIRCUIT_BREAKER_THRESHOLD:
                        guard.report_signal(e, source='cost crawler')
                        aborted_due_to_block = True
                        log('⛔ circuit breaker 발동 — 글로벌 차단 락, 즉시 중단')
                        break

                # driver가 죽었으면 즉시 재생성
                if _is_dead_driver_error(e):
                    log('driver 죽음 감지 → 재생성')
                    _safe_quit(driver)
                    driver = None
                    try:
                        driver = _new_driver(kill_existing=True)
                        accounts_since_restart = 0
                    except Exception as e2:
                        logger.error(f'driver 재생성 실패: {e2}')
                        # 다음 루프에서 재시도
                        continue
            else:
                consecutive_block_signals = 0  # 성공 시 리셋

            # 대기 전 빈 페이지로 이동 — 11번가 JS가 Chrome 크래시 유발 방지
            try:
                driver.get('about:blank')
            except Exception:
                pass

            # 사람 패턴: 마지막 계정 아니면 잠시 대기
            if idx < total_accounts:
                wait = random.uniform(*INTER_ACCOUNT_SLEEP)
                log(f'다음 계정까지 {wait:.1f}s 대기')
                time.sleep(wait)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        stop_display()

    summary = f'11번가 수집 완료: 성공={collected} 실패={failed}'
    if aborted_due_to_block:
        summary += ' (차단신호로 조기 중단)'
    if log_fn:
        log_fn(summary)

    # 텔레그램 결과 발송
    try:
        _send_telegram_report(collected, failed, accounts)
    except Exception as e:
        logger.warning(f'텔레그램 발송 실패: {e}')

    # 17시 이후 실행이면, 17시 이후 발생한 광고비를 계정별로 추가 알림
    try:
        if _alert_evening_cpc(after_hour=17):
            logger.info('17시 이후 광고비 발생 알림 전송')
    except Exception as e:
        logger.warning(f'17시 이후 광고비 알림 실패: {e}')

    guard.release_global_lock()   # 전역 락 해제 (동시 크롤 금지 유지)
    # 부분 실패(일부 계정)는 계정별 notify_failure(연속2회+1일1회 게이팅)가 처리 →
    # 예약 알림은 '심각'한 경우만(차단중단 / 전부실패)으로 한정해 텔레그램 도배 방지.
    if scheduled and aborted_due_to_block:
        guard.notify_problem('11번가광고비', f'예약 크롤 차단으로 중단 — 수집 {collected} / 실패 {failed}')
    elif scheduled and collected == 0 and failed:
        guard.notify_problem('11번가광고비', f'예약 크롤 전부 실패 — 실패 {failed}건 (수집 0)')
    return {
        'collected': collected,
        'failed': failed,
        'aborted_due_to_block': aborted_due_to_block,
        'skipped_recent': len(skipped_recent),
    }
