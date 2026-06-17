"""지마켓 ESM 수동 로그인(캡차는 본인이 VNC로 직접 풀이) → 쿠키 저장 → 검증.
차단 방지: 동시크롤 금지, 계정1개·로그인1회, 자동 캡차풀이 안 함(사람이 입력).
사용: python3 -u manual_login_vnc.py [login_id]   (기본 rejoice666)
진행상황: /tmp/gmkt_manual_login.log 로 출력.
"""
import os, sys, time, subprocess, signal

LOGIN_ID = sys.argv[1] if len(sys.argv) > 1 else 'rejoice666'
DISPLAY = ':99'
VNC_PORT = '5900'
VNC_PASSFILE = '/tmp/.esmvnc'
WAIT_MIN = 25          # 사람이 캡차 풀 시간(최대)
BALANCE_PAGE = 'https://www.esmplus.com/Member/Settle/GmktSellBalanceManagement'


def log(m):
    print('[%s] %s' % (time.strftime('%H:%M:%S'), m), flush=True)


# 1) Xvfb :99 기동
xvfb = subprocess.Popen(['Xvfb', DISPLAY, '-screen', '0', '1920x1080x24'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)
os.environ['DISPLAY'] = DISPLAY
log('Xvfb 기동 %s (pid %s)' % (DISPLAY, xvfb.pid))

# 2) VNC 비밀번호 저장 + x11vnc 기동(LAN에서 본인 접속)
subprocess.run(['x11vnc', '-storepasswd', 'esm2026', VNC_PASSFILE],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
vnc = subprocess.Popen(['x11vnc', '-display', DISPLAY, '-rfbauth', VNC_PASSFILE,
                        '-rfbport', VNC_PORT, '-forever', '-shared', '-noxdamage'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
log('x11vnc 기동 포트 %s (비밀번호 esm2026)' % VNC_PORT)
log('>>> VNC 접속: 192.168.45.100:%s  / 비번 esm2026  <<<' % VNC_PORT)

import django  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from selenium.webdriver.common.by import By  # noqa: E402
from crawlers.browser import create_driver, stop_display  # noqa: E402
from crawlers.gmarket_cost_crawler import (  # noqa: E402
    _esm_logged_in, _save_cookies, _try_cookie_login, _dismiss_esm_popups)
from apps.cpc.models import CrawlerAccount  # noqa: E402

a = CrawlerAccount.objects.get(login_id=LOGIN_ID, platform='gmarket')
driver = None
result = 'UNKNOWN'
try:
    driver = create_driver(kill_existing=False)
    log('[%s] 로그인 페이지 진입 + id/pw 입력(캡차는 본인이 VNC로 입력)' % LOGIN_ID)
    driver.get('https://www.esmplus.com/')
    time.sleep(3)
    if not _esm_logged_in(driver):
        for b in driver.find_elements(By.XPATH, "//button[contains(@class,'button__tab')]"):
            if (b.text or '').strip() == '지마켓':
                driver.execute_script("arguments[0].click();", b); time.sleep(1); break
        try:
            idf = driver.find_element(By.ID, 'typeMemberInputId01')
            pwf = driver.find_element(By.ID, 'typeMemberInputPassword01')
            idf.clear(); idf.send_keys(a.login_id)
            pwf.clear(); pwf.send_keys(a.password_enc)
            log('id/pw 입력 완료 — 이제 VNC 화면에서 캡차 입력 후 [로그인] 눌러주세요.')
        except Exception as e:
            log('입력단계 예외(무시 가능, VNC에서 직접 입력): %s' % e)

    # 3) 사람이 캡차 풀고 로그인할 때까지 폴링(최대 WAIT_MIN분)
    deadline = time.time() + WAIT_MIN * 60
    ok = False
    last = 0
    while time.time() < deadline:
        time.sleep(5)
        try:
            if _esm_logged_in(driver):
                _dismiss_esm_popups(driver)
                ok = True
                break
        except Exception:
            pass
        if time.time() - last >= 60:
            left = int((deadline - time.time()) / 60)
            log('대기중... 아직 로그인 전(캡차 입력 필요). 남은 %d분. 현재URL=%s'
                % (left, (driver.current_url or '')[:60]))
            last = time.time()

    if not ok:
        result = 'TIMEOUT_NO_LOGIN'
        log('[%s] 시간초과 — 로그인 미완료' % LOGIN_ID)
    else:
        log('[%s] 로그인 성공 감지 → 쿠키 저장' % LOGIN_ID)
        driver.get(BALANCE_PAGE)
        time.sleep(4)
        _save_cookies(driver, a)
        log('[%s] 쿠키 저장 완료(len=%d). 검증 시작...' % (LOGIN_ID, len(a.cookie_data or '')))
        # 4) 검증 — 새 드라이버로 쿠키 로그인 시도(크롤러가 캡차 없이 되는지)
        driver.quit(); driver = None
        time.sleep(2)
        a.refresh_from_db()
        v = create_driver(kill_existing=False)
        try:
            verified = _try_cookie_login(v, a)
        finally:
            v.quit()
        result = 'OK_VERIFIED' if verified else 'SAVED_BUT_VERIFY_FAILED'
        log('[%s] 검증결과: %s' % (LOGIN_ID, result))
finally:
    log('[%s] RESULT=%s' % (LOGIN_ID, result))
    try:
        if driver: driver.quit()
    except Exception:
        pass
    try: stop_display()
    except Exception: pass
    for p in (vnc, xvfb):
        try: p.send_signal(signal.SIGTERM)
        except Exception: pass
    log('정리 완료(VNC/Xvfb 종료)')
