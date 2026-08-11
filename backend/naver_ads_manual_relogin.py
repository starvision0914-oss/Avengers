"""네이버 광고센터(ads.naver.com) 계정 수동 1회 재로그인 대기 스크립트.
QR 재로그인이 필요한 계정 전용 — 브라우저만 열어두고, 사람이 VNC(192.168.45.100:5905)로
직접 들어가서 네이버 앱으로 QR을 스캔. NAVER_ADS_AVAILABLE_USER 쿠키가 잡히면
naver_ads_cookies.json에 저장 후 종료.
사용: python3 -u naver_ads_manual_relogin.py [login_id]  (기본 rejoice666)
로그: /tmp/naver_ads_manual_relogin.log
"""
import os
import sys
import json
import time

os.environ['DISPLAY'] = ':99'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django  # noqa: E402
django.setup()

from crawlers.browser import create_driver  # noqa: E402
from selenium.webdriver.common.by import By  # noqa: E402

LOGIN_ID = sys.argv[1] if len(sys.argv) > 1 else 'rejoice666'
MAX_WAIT_MIN = 20
COOKIE_FILE = os.path.join(os.path.dirname(__file__), 'crawlers/naver_ads_cookies.json')


def log(m):
    print('[%s] %s' % (time.strftime('%H:%M:%S'), m), flush=True)


driver = create_driver(kill_existing=False)
result = 'TIMEOUT'
try:
    driver.get('https://ads.naver.com/')
    time.sleep(3)
    try:
        clicked = False
        for _ in range(15):   # 최대 15초, 1초 간격 폴링 (ads.naver.com→nid.naver.com 리다이렉트 대기)
            try:
                el = driver.find_element(By.PARTIAL_LINK_TEXT, 'QR')
                if el.is_displayed():
                    driver.execute_script('arguments[0].click();', el)
                    clicked = True
                    break
            except Exception:
                pass
            time.sleep(1)
        log('QR 코드 로그인 탭 클릭함' if clicked else 'QR 탭 못찾음(최대 15초 대기 후)')
        if clicked:
            time.sleep(1.5)
    except Exception as e:
        log('QR 탭 조사 실패: %s' % e)
    log('네이버 광고센터 열림 — VNC(192.168.45.100:5905)로 들어와서 %s 네이버 앱으로 QR 스캔해주세요.' % LOGIN_ID)
    deadline = time.time() + MAX_WAIT_MIN * 60
    last_log = 0
    while time.time() < deadline:
        time.sleep(3)
        cookies = driver.get_cookies()
        has_ads = any(c['name'] == 'NAVER_ADS_AVAILABLE_USER' for c in cookies)
        has_aut = any(c['name'] == 'NID_AUT' for c in cookies)
        if has_ads and has_aut:
            result = 'OK'
            break
        if time.time() - last_log >= 30:
            log('로그인 대기 중... 남은 %d분' % int((deadline - time.time()) / 60))
            last_log = time.time()

    if result == 'OK':
        cookies = driver.get_cookies()
        try:
            with open(COOKIE_FILE) as f:
                data = json.load(f)
        except Exception:
            data = {}
        data[LOGIN_ID] = cookies
        with open(COOKIE_FILE, 'w') as f:
            json.dump(data, f, ensure_ascii=False)
        log('로그인 확인됨 — 쿠키 %d개 저장 완료 (NAVER_ADS_AVAILABLE_USER 포함)' % len(cookies))
    else:
        log('시간 초과 — 로그인 미확인, 쿠키 저장 안 함')
finally:
    log('RESULT=%s' % result)
    try:
        driver.quit()
    except Exception:
        pass
