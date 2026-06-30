"""지마켓 ESM 2단계 인증(OTP) 릴레이 스크립트
흐름:
  1) ESM 로그인 시도 → 2단계 인증 페이지 대기
  2) 스크린샷 → 텔레그램 전송 + 프론트 public 저장
  3) OTP 입력칸이 있으면 텔레그램 답장 대기 후 입력
     OTP 입력칸 없으면(푸시인증) 폰에서 승인 후 인증 완료 대기
  4) 로그인 성공 시 쿠키 저장+검증
사용: python3 -u gmarket_2fa_relay.py [login_id]   (기본 rejoice666)
"""
import os, sys, time, shutil

LOGIN_ID = sys.argv[1] if len(sys.argv) > 1 else 'rejoice666'
ANSWER = '/tmp/captcha_answer.txt'
PUB = '/home/rejoice888/Avengers/frontend/public/captcha.png'
TMP_SHOT = '/tmp/gmkt_2fa.png'
MAX_WAIT_MIN = 10

def log(m):
    print('[%s] %s' % (time.strftime('%H:%M:%S'), m), flush=True)

os.environ.setdefault('DISPLAY', ':99')
import subprocess
if subprocess.run(['pgrep', '-f', 'Xvfb :99'], stdout=subprocess.DEVNULL).returncode != 0:
    subprocess.Popen(['Xvfb', ':99', '-screen', '0', '1920x1080x24'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)

import django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from crawlers.browser import create_driver, stop_display
from crawlers.gmarket_cost_crawler import _esm_logged_in, _save_cookies, _try_cookie_login
from apps.cpc.models import CrawlerAccount

PENDING = '/tmp/captcha_pending'
LOGIN_URL = 'https://ad.esmplus.com/'

def _telegram_send(text):
    try:
        import requests
        from apps.cpc.models import TelegramConfig, TelegramRecipient
        cfg = TelegramConfig.objects.first()
        if not cfg or not cfg.bot_token:
            return
        url = 'https://api.telegram.org/bot%s/sendMessage' % cfg.bot_token
        for r in TelegramRecipient.objects.filter(is_active=True):
            try:
                requests.post(url, json={'chat_id': r.chat_id, 'text': text}, timeout=10)
            except Exception:
                pass
        log('텔레그램 메시지 전송')
    except Exception as e:
        log('텔레그램 전송 실패: %s' % e)

def _telegram_photo(path, caption):
    try:
        import requests
        from apps.cpc.models import TelegramConfig, TelegramRecipient
        cfg = TelegramConfig.objects.first()
        if not cfg or not cfg.bot_token:
            return
        url = 'https://api.telegram.org/bot%s/sendPhoto' % cfg.bot_token
        for r in TelegramRecipient.objects.filter(is_active=True):
            try:
                with open(path, 'rb') as fh:
                    requests.post(url, data={'chat_id': r.chat_id, 'caption': caption},
                                  files={'photo': fh}, timeout=15)
            except Exception:
                pass
        log('텔레그램 사진 전송')
    except Exception as e:
        log('텔레그램 사진 전송 실패: %s' % e)

def screenshot_and_send(driver, label=''):
    try:
        driver.save_screenshot(TMP_SHOT)
        shutil.copy(TMP_SHOT, PUB)
        log('스크린샷 저장 → http://192.168.45.100:5173/captcha.png')
        _telegram_photo(TMP_SHOT, '지마켓 %s 2단계 인증 화면 %s' % (LOGIN_ID, label))
    except Exception as e:
        log('스크린샷 실패: %s' % e)

def find_otp_input(driver):
    for inp in driver.find_elements(By.XPATH, "//input"):
        try:
            if not inp.is_displayed():
                continue
            idv = (inp.get_attribute('id') or '').lower()
            nm = (inp.get_attribute('name') or '').lower()
            ph = (inp.get_attribute('placeholder') or '').lower()
            tp = (inp.get_attribute('type') or '').lower()
            blob = idv + ' ' + nm + ' ' + ph
            if any(k in blob for k in ('otp', 'certno', 'authno', 'securityno', 'inputOtp',
                                        '인증번호', 'auth', 'code', 'number')):
                return inp
            if tp in ('tel', 'number') and inp.is_enabled():
                return inp
        except Exception:
            continue
    return None

def wait_otp_reply():
    open(ANSWER, 'w').close()
    open(PENDING, 'w').close()
    deadline = time.time() + MAX_WAIT_MIN * 60
    last = 0
    try:
        while time.time() < deadline:
            time.sleep(3)
            try:
                with open(ANSWER) as f:
                    v = f.read().strip()
                if v:
                    open(ANSWER, 'w').close()
                    return v
            except Exception:
                pass
            if time.time() - last >= 60:
                log('OTP 답 대기 중... 남은 %d분' % int((deadline - time.time()) / 60))
                last = time.time()
        return None
    finally:
        try:
            os.remove(PENDING)
        except Exception:
            pass

acct = CrawlerAccount.objects.get(login_id=LOGIN_ID, platform='gmarket')
driver = None
result = 'UNKNOWN'

try:
    driver = create_driver(kill_existing=False)

    # 쿠키 로그인 먼저 시도
    if _try_cookie_login(driver, acct):
        log('[%s] 쿠키 로그인 성공 — 2단계 인증 불필요' % LOGIN_ID)
        result = 'OK_COOKIE'
    else:
        log('[%s] 쿠키 만료 → 풀 로그인 시도' % LOGIN_ID)
        driver.delete_all_cookies()
        driver.get(LOGIN_URL)
        time.sleep(3)

        # 지마켓 탭 선택
        try:
            for b in driver.find_elements(By.XPATH, "//input[@name='rdoSiteSelect']"):
                if b.get_attribute('value') == 'GMKT':
                    driver.execute_script("arguments[0].click();", b)
                    time.sleep(0.5)
                    break
        except Exception:
            pass

        # id/pw 입력
        try:
            idf = driver.find_element(By.ID, 'SellerId')
            pwf = driver.find_element(By.ID, 'SellerPassword')
            idf.clear(); idf.send_keys(acct.login_id)
            pwf.clear(); pwf.send_keys(acct.password_enc)
            log('[%s] id/pw 입력 완료' % LOGIN_ID)
            # 로그인 버튼
            try:
                driver.find_element(By.XPATH, '//img[@alt="로그인"]').click()
            except Exception:
                try:
                    driver.find_element(By.XPATH,
                        "//button[contains(@class,'button--blue') and contains(.,'로그인')]").click()
                except Exception as e:
                    log('로그인 버튼 클릭 실패: %s' % e)
        except Exception as e:
            log('id/pw 입력 실패: %s' % e)

        time.sleep(5)
        url = driver.current_url.lower()
        log('로그인 후 URL: %s' % url)

        if _esm_logged_in(driver):
            log('[%s] 2단계 인증 없이 바로 로그인 성공' % LOGIN_ID)
            result = 'OK_DIRECT'
        elif 'logon' in url or 'signin' in url or '2' in driver.page_source[:2000]:
            log('[%s] 2단계 인증 페이지 감지' % LOGIN_ID)
            page = driver.page_source

            screenshot_and_send(driver, '(첫 화면)')

            otp_inp = find_otp_input(driver)
            if otp_inp:
                log('[%s] OTP 입력칸 발견 → 텔레그램 답장 대기' % LOGIN_ID)
                _telegram_send(
                    '🔐 지마켓 [%s] 2단계 인증\n'
                    'OTP/인증번호를 이 채팅에 답장해주세요 (숫자만)\n'
                    '화면: http://192.168.45.100:5173/captcha.png' % LOGIN_ID
                )
                otp_code = wait_otp_reply()
                if not otp_code:
                    result = 'TIMEOUT'
                    log('[%s] OTP 타임아웃(%d분)' % (LOGIN_ID, MAX_WAIT_MIN))
                else:
                    log('[%s] OTP 코드 수신: %s' % (LOGIN_ID, otp_code))
                    try:
                        otp_inp = find_otp_input(driver)
                        if otp_inp:
                            otp_inp.clear()
                            otp_inp.send_keys(otp_code)
                        # 확인 버튼 클릭
                        for xpath in (
                            "//button[contains(.,'확인')]",
                            "//button[contains(.,'인증')]",
                            "//button[contains(.,'다음')]",
                            "//input[@type='submit']",
                        ):
                            try:
                                btn = driver.find_element(By.XPATH, xpath)
                                if btn.is_displayed():
                                    btn.click()
                                    log('확인 버튼 클릭: %s' % xpath)
                                    break
                            except Exception:
                                continue
                        time.sleep(5)
                    except Exception as e:
                        log('OTP 입력 실패: %s' % e)
            else:
                log('[%s] OTP 입력칸 없음 → 푸시/앱 인증 방식' % LOGIN_ID)
                _telegram_send(
                    '🔐 지마켓 [%s] 2단계 인증 (푸시/앱 방식)\n'
                    '스마트폰에서 인증을 승인해주세요.\n'
                    '화면: http://192.168.45.100:5173/captcha.png\n'
                    '승인 완료 후 이 채팅에 "완료"라고 답장해주세요.' % LOGIN_ID
                )
                otp_code = wait_otp_reply()
                if not otp_code:
                    log('[%s] 푸시 인증 타임아웃' % LOGIN_ID)
                    result = 'TIMEOUT'

            # 로그인 결과 확인
            for _ in range(10):
                time.sleep(2)
                if _esm_logged_in(driver):
                    break

            if _esm_logged_in(driver):
                log('[%s] 2단계 인증 통과 → 로그인 성공' % LOGIN_ID)
                result = 'OK_2FA'
            else:
                log('[%s] 2단계 인증 후에도 로그인 실패' % LOGIN_ID)
                screenshot_and_send(driver, '(인증 후 상태)')
                result = 'FAIL_2FA'
        else:
            log('[%s] 알 수 없는 상태 URL=%s' % (LOGIN_ID, url))
            screenshot_and_send(driver, '(알 수 없는 상태)')
            result = 'FAIL_UNKNOWN'

    # 성공 시 쿠키 저장+검증
    if result.startswith('OK'):
        _save_cookies(driver, acct)
        acct.refresh_from_db()
        log('[%s] 쿠키 저장 완료 (len=%d) → 검증' % (LOGIN_ID, len(acct.cookie_data or '')))
        driver.quit(); driver = None
        time.sleep(2)
        vdrv = create_driver(kill_existing=False)
        try:
            verified = _try_cookie_login(vdrv, acct)
        finally:
            vdrv.quit()
        if verified:
            log('[%s] 쿠키 검증 성공 ✓' % LOGIN_ID)
            _telegram_send('✅ 지마켓 [%s] 로그인+쿠키 갱신 완료!' % LOGIN_ID)
            result = 'OK_VERIFIED'
        else:
            log('[%s] 쿠키 검증 실패' % LOGIN_ID)
            result = 'SAVED_BUT_VERIFY_FAILED'

finally:
    log('[%s] RESULT=%s' % (LOGIN_ID, result))
    try:
        if driver:
            driver.quit()
    except Exception:
        pass
    for f in (PUB,):
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass
    try:
        stop_display()
    except Exception:
        pass
