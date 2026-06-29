"""
스마트스토어 광고센터(ads.naver.com) QR코드 로그인 릴레이
캡챠 없이 QR 스캔만으로 로그인 → 완전한 쿠키 추출 → DB 저장

사용: python3 ss_ad_login_relay.py [naver_id]
예)  python3 ss_ad_login_relay.py rejoice999
"""
import os, sys, time, shutil, json, re

LOGIN_ID  = sys.argv[1] if len(sys.argv) > 1 else 'rejoice999'
PUB       = '/home/rejoice888/Avengers/frontend/public/captcha.png'
TMP_SHOT  = '/tmp/ss_ad_captcha.png'
COOKIE_FILE = os.path.join(os.path.dirname(__file__), 'crawlers/naver_ads_cookies.json')
QR_WAIT_MIN = 10   # QR 스캔 대기 최대 10분

# VNC(:99) 상시 실행 중 — 브라우저를 VNC 화면에 띄워 사용자가 QR 스캔 가능
os.environ['DISPLAY'] = ':99'

LOGIN_URL = 'https://nid.naver.com/nidlogin.login?url=https%3A%2F%2Fads.naver.com%2F'
ADS_HOME  = 'https://ads.naver.com/'

import django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from crawlers.browser import create_driver
from apps.smartstore.models import SmartStoreAccount


def log(m):
    print('[%s] %s' % (time.strftime('%H:%M:%S'), m), flush=True)


def _telegram_photo(path, caption):
    try:
        import requests
        from apps.cpc.models import TelegramConfig, TelegramRecipient
        cfg = TelegramConfig.objects.first()
        if not cfg or not cfg.bot_token:
            log('텔레그램 설정 없음')
            return
        url = 'https://api.telegram.org/bot%s/sendPhoto' % cfg.bot_token
        for r in TelegramRecipient.objects.filter(is_active=True):
            try:
                with open(path, 'rb') as fh:
                    requests.post(url, data={'chat_id': r.chat_id, 'caption': caption},
                                  files={'photo': fh}, timeout=15)
            except Exception as e:
                log(f'텔레그램 전송 실패: {e}')
        log('텔레그램 전송 완료')
    except Exception as e:
        log(f'텔레그램 오류: {e}')


def screenshot(driver, caption):
    """QR코드 영역 스크린샷 → Telegram 전송."""
    try:
        # QR 이미지 요소로 스크롤
        try:
            qr_el = driver.find_element(By.CSS_SELECTOR, 'canvas, img[src*="qr"], .qr_area, #qrcode')
            driver.execute_script("arguments[0].scrollIntoView({block:'center'})", qr_el)
        except Exception:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2)")
        time.sleep(0.5)

        body_h = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(600, max(700, body_h))
        time.sleep(0.5)
        driver.save_screenshot(TMP_SHOT)
        shutil.copy(TMP_SHOT, PUB)
        log(f'스크린샷 → {PUB}')
        _telegram_photo(TMP_SHOT, caption)
    except Exception as e:
        log(f'스크린샷 오류: {e}')


def is_logged_in(driver):
    url = driver.current_url
    return 'ads.naver.com' in url and 'nid.naver' not in url and 'nidlogin' not in url


def save_cookies(driver):
    """로그인 완료 후 ads.naver.com 전체 쿠키 저장."""
    try:
        cookies = driver.get_cookies()
        data = {}
        if os.path.exists(COOKIE_FILE):
            with open(COOKIE_FILE) as f:
                data = json.load(f)
        key = LOGIN_ID.split('@')[0]
        data[key] = cookies
        with open(COOKIE_FILE, 'w') as f:
            json.dump(data, f, ensure_ascii=False)
        names = [c['name'] for c in cookies]
        log(f'쿠키 저장: {len(cookies)}개 {names}')
        return key
    except Exception as e:
        log(f'쿠키 저장 오류: {e}')
        return None


def get_ad_account_id(driver):
    """현재 URL·페이지에서 광고계정 ID 추출."""
    try:
        url = driver.current_url
        m = re.search(r'/ad-account/(\d+)', url)
        if m:
            return m.group(1)
        src = driver.page_source
        for pat in [r'"adAccountId"\s*:\s*"?(\d+)"?', r'"accountId"\s*:\s*(\d+)']:
            m = re.search(pat, src)
            if m:
                return m.group(1)
        links = driver.find_elements(By.XPATH, "//a[contains(@href,'/ad-account/')]")
        for lk in links:
            href = lk.get_attribute('href') or ''
            m = re.search(r'/ad-account/(\d+)', href)
            if m:
                return m.group(1)
    except Exception as e:
        log(f'ad_account_id 추출 오류: {e}')
    return None


# ── 메인 ──
account = SmartStoreAccount.objects.filter(
    naver_ad_login_id=LOGIN_ID.split('@')[0]
).first()
if account:
    log(f'계정: {account.display_name} ({account.login_id})')
else:
    log(f'SmartStoreAccount에서 {LOGIN_ID} 미발견 — 쿠키만 저장')

driver = None
result = 'UNKNOWN'
try:
    driver = create_driver(kill_existing=True)
    driver.set_window_size(600, 800)
    driver.get(LOGIN_URL)
    time.sleep(3)

    if is_logged_in(driver):
        log('이미 로그인 상태')
    else:
        # QR코드 탭 클릭
        try:
            qr_tab = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//*[contains(text(),'QR코드') or contains(text(),'QR')]"
                    "[not(self::title)][not(self::script)]"
                ))
            )
            qr_tab.click()
            time.sleep(2)
            log('QR코드 탭 클릭')
        except Exception as e:
            log(f'QR탭 클릭 실패({e}) — 스크린샷 확인')

        # QR 스크린샷 → Telegram
        screenshot(driver,
            f'[네이버 광고센터] {LOGIN_ID}\n'
            f'네이버 앱으로 QR코드를 스캔해주세요\n'
            f'(캡챠 없이 바로 로그인됩니다)')

        # 로그인 완료 대기 (최대 QR_WAIT_MIN분)
        log(f'QR 스캔 대기 중 (최대 {QR_WAIT_MIN}분)...')
        deadline = time.time() + QR_WAIT_MIN * 60
        last_shot = time.time()
        while time.time() < deadline:
            time.sleep(3)
            if is_logged_in(driver):
                log('로그인 성공!')
                break
            # 2분마다 QR 갱신 스크린샷
            if time.time() - last_shot >= 120:
                screenshot(driver,
                    f'[광고센터] {LOGIN_ID} QR 갱신\n네이버 앱으로 스캔해주세요')
                last_shot = time.time()
        else:
            log('QR 스캔 타임아웃')
            result = 'TIMEOUT'

    if is_logged_in(driver):
        # ads.naver.com 메인으로 이동해서 완전한 쿠키 확보
        driver.get(ADS_HOME)
        time.sleep(4)

        cookie_key = save_cookies(driver)
        ad_account_id = get_ad_account_id(driver)
        log(f'광고계정 ID: {ad_account_id}')

        if account:
            update = {}
            if cookie_key:
                update['naver_ad_login_id'] = cookie_key
            if ad_account_id and not account.naver_ad_account_id:
                update['naver_ad_account_id'] = ad_account_id
            if update:
                SmartStoreAccount.objects.filter(pk=account.pk).update(**update)
                log(f'DB 저장: {account.display_name} → {update}')

        result = 'OK'
    elif result == 'UNKNOWN':
        result = 'FAIL'

finally:
    log(f'RESULT={result}')
    try:
        if driver:
            driver.quit()
    except Exception:
        pass
    try:
        if os.path.exists(PUB):
            os.remove(PUB)
    except Exception:
        pass
