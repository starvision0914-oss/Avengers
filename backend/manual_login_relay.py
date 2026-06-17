"""지마켓 ESM 수동 로그인(스크린샷 릴레이) — 캡차는 본인이 이미지 보고 문자 입력.
차단 방지: 동시크롤 금지, 계정1개, 캡차 자동풀이 안 함(사람이 답 제공).
흐름:
  1) id/pw 자동입력 → 캡차 영역 스크린샷을 프론트 public(URL)로 저장
  2) 본인이 URL 이미지 보고, 답을 /tmp/captcha_answer.txt 에 기록(=Claude가 대신 기록)
  3) 스크립트가 답을 캡차칸에 입력+로그인 → 성공시 쿠키저장+검증, 실패시 새 이미지로 재시도
사용: python3 -u manual_login_relay.py [login_id]   (기본 rejoice666)
로그: /tmp/gmkt_relay.log
"""
import os, sys, time, shutil

LOGIN_ID = sys.argv[1] if len(sys.argv) > 1 else 'rejoice666'
ANSWER = '/tmp/captcha_answer.txt'
PUB = '/home/rejoice888/Avengers/frontend/public/captcha.png'
TMP_SHOT = '/tmp/gmkt_captcha.png'
BALANCE_PAGE = 'https://www.esmplus.com/Member/Settle/GmktSellBalanceManagement'
MAX_ROUNDS = 8           # 캡차 재시도 횟수
ANSWER_WAIT_MIN = 25     # 한 라운드에서 답 기다리는 최대(분)


def log(m):
    print('[%s] %s' % (time.strftime('%H:%M:%S'), m), flush=True)


os.environ.setdefault('DISPLAY', ':99')
# Xvfb 보장
import subprocess
if subprocess.run(['pgrep', '-f', 'Xvfb :99'], stdout=subprocess.DEVNULL).returncode != 0:
    subprocess.Popen(['Xvfb', ':99', '-screen', '0', '1920x1080x24'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)

import django  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from selenium.webdriver.common.by import By  # noqa: E402
from crawlers.browser import create_driver, stop_display  # noqa: E402
from crawlers.gmarket_cost_crawler import (  # noqa: E402
    _esm_logged_in, _save_cookies, _try_cookie_login, _dismiss_esm_popups)
from apps.cpc.models import CrawlerAccount  # noqa: E402


def find_captcha_input(driver):
    for inp in driver.find_elements(By.XPATH, "//input"):
        try:
            if not inp.is_displayed():
                continue
            ph = (inp.get_attribute('placeholder') or '')
            idv = (inp.get_attribute('id') or '')
            nm = (inp.get_attribute('name') or '')
            blob = (ph + ' ' + idv + ' ' + nm).lower()
            if '자동입력' in ph or 'captcha' in blob or 'capt' in blob or 'security' in blob:
                return inp
        except Exception:
            continue
    return None


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
        log('텔레그램으로 캡차 이미지 전송됨')
    except Exception as e:
        log('텔레그램 전송 실패: %s' % e)


def shot(driver, tag=''):
    try:
        driver.save_screenshot(TMP_SHOT)
        shutil.copy(TMP_SHOT, PUB)
        log('캡차 이미지 저장 %s → http://192.168.45.100:5173/captcha.png (새로고침해서 보세요)' % tag)
        _telegram_photo(TMP_SHOT, '지마켓 %s 캡차 %s — 이 문자를 텔레그램에 답장해주세요' % (LOGIN_ID, tag))
    except Exception as e:
        log('스크린샷 실패: %s' % e)


PENDING = '/tmp/captcha_pending'


def wait_answer():
    """답 파일/텔레그램훅 답 올 때까지 폴링. 한 줄 답 반환(없으면 None=타임아웃).
    대기 동안 /tmp/captcha_pending 플래그 ON → 텔레그램봇이 답장을 캡차로 인식해 ANSWER에 기록."""
    open(ANSWER, 'w').close()
    open(PENDING, 'w').close()
    deadline = time.time() + ANSWER_WAIT_MIN * 60
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
                log('답 대기중(채팅 또는 텔레그램 답장)... 남은 %d분'
                    % int((deadline - time.time()) / 60))
                last = time.time()
        return None
    finally:
        try:
            os.remove(PENDING)
        except Exception:
            pass


a = CrawlerAccount.objects.get(login_id=LOGIN_ID, platform='gmarket')
driver = None
result = 'UNKNOWN'
try:
    driver = create_driver(kill_existing=False)
    driver.get('https://www.esmplus.com/')
    time.sleep(3)
    if not _esm_logged_in(driver):
        for b in driver.find_elements(By.XPATH, "//button[contains(@class,'button__tab')]"):
            if (b.text or '').strip() == '지마켓':
                driver.execute_script("arguments[0].click();", b); time.sleep(1); break
        idf = driver.find_element(By.ID, 'typeMemberInputId01')
        pwf = driver.find_element(By.ID, 'typeMemberInputPassword01')
        idf.clear(); idf.send_keys(a.login_id)
        pwf.clear(); pwf.send_keys(a.password_enc)
        log('[%s] id/pw 입력 완료' % LOGIN_ID)

    def click_login():
        try:
            driver.find_element(
                By.XPATH, "//button[contains(@class,'button--blue') and contains(.,'로그인')]").click()
            return True
        except Exception as e:
            log('로그인 버튼 클릭 예외: %s' % e); return False

    # 캡차는 로그인 1회 클릭해야 등장 → 먼저 클릭해 캡차 surface
    if not _esm_logged_in(driver) and find_captcha_input(driver) is None:
        log('[%s] 캡차 띄우기용 로그인 클릭(1회)' % LOGIN_ID)
        click_login()
        for _ in range(8):
            time.sleep(1.5)
            if _esm_logged_in(driver) or find_captcha_input(driver) is not None:
                break
        if _esm_logged_in(driver):
            log('[%s] 캡차 없이 바로 로그인됨' % LOGIN_ID)

    for rnd in range(1, MAX_ROUNDS + 1):
        if _esm_logged_in(driver):
            break
        cap = find_captcha_input(driver)
        if cap is None:
            ids = [(i.get_attribute('id'), i.get_attribute('placeholder'))
                   for i in driver.find_elements(By.XPATH, "//input") if i.is_displayed()]
            log('캡차 입력칸 못찾음. 보이는 input들=%s → 로그인 재클릭' % ids)
            click_login(); time.sleep(3)
            continue
        shot(driver, '(라운드 %d)' % rnd)
        ans = wait_answer()
        if not ans:
            result = 'TIMEOUT_NO_ANSWER'
            log('답 미입력 시간초과(라운드 %d)' % rnd); break
        log('[%s] 라운드 %d 답수신="%s" → 입력+로그인' % (LOGIN_ID, rnd, ans))
        try:
            cap = find_captcha_input(driver)
            if cap:
                cap.clear(); cap.send_keys(ans)
            driver.find_element(
                By.XPATH, "//button[contains(@class,'button--blue') and contains(.,'로그인')]").click()
        except Exception as e:
            log('입력/클릭 예외: %s' % e)
        # 로그인 결과 대기
        for _ in range(8):
            time.sleep(2)
            if _esm_logged_in(driver):
                break
        if _esm_logged_in(driver):
            _dismiss_esm_popups(driver)
            log('[%s] 로그인 성공!' % LOGIN_ID); break
        else:
            log('[%s] 라운드 %d 실패(캡차 오답/만료 추정) → 새 이미지' % (LOGIN_ID, rnd))

    if not _esm_logged_in(driver):
        if result == 'UNKNOWN':
            result = 'FAIL_AFTER_ROUNDS'
    else:
        driver.get(BALANCE_PAGE); time.sleep(4)
        _save_cookies(driver, a)
        a.refresh_from_db()
        log('[%s] 쿠키 저장(len=%d) → 검증' % (LOGIN_ID, len(a.cookie_data or '')))
        driver.quit(); driver = None; time.sleep(2)
        v = create_driver(kill_existing=False)
        try:
            verified = _try_cookie_login(v, a)
        finally:
            v.quit()
        result = 'OK_VERIFIED' if verified else 'SAVED_BUT_VERIFY_FAILED'
finally:
    log('[%s] RESULT=%s' % (LOGIN_ID, result))
    try:
        if driver: driver.quit()
    except Exception:
        pass
    try:
        if os.path.exists(PUB):
            os.remove(PUB)
    except Exception:
        pass
    try: stop_display()
    except Exception: pass
