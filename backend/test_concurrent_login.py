"""지마켓 동시 로그인 부하 테스트 — 풀로그인 1회, 캡차/차단 감지. 가볍게(1회만)."""
import os, sys, time, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from selenium.webdriver.common.by import By
from crawlers.browser import create_driver, stop_display
from crawlers.gmarket_cost_crawler import _esm_logged_in, _dismiss_esm_popups
from apps.cpc.models import CrawlerAccount

LID = sys.argv[1]
LOG = '/tmp/gmkt_concurrent_test.log'


def log(m):
    line = f'[{time.strftime("%H:%M:%S")}] [{LID}] {m}'
    print(line, flush=True)
    with open(LOG, 'a') as f:
        f.write(line + '\n')


a = CrawlerAccount.objects.get(login_id=LID, platform='gmarket')
d = create_driver(kill_existing=False)   # 서로 안 죽이게
result = 'UNKNOWN'
try:
    log('풀로그인 시작')
    d.get('https://www.esmplus.com/'); time.sleep(3)
    if not _esm_logged_in(d):
        for b in d.find_elements(By.XPATH, "//button[contains(@class,'button__tab')]"):
            if (b.text or '').strip() == '지마켓':
                d.execute_script("arguments[0].click();", b); time.sleep(1); break
        try:
            d.find_element(By.ID, 'typeMemberInputId01').send_keys(a.login_id)
            d.find_element(By.ID, 'typeMemberInputPassword01').send_keys(a.password_enc)
            d.find_element(By.XPATH, "//button[contains(@class,'button--blue') and contains(.,'로그인')]").click()
        except Exception as e:
            log(f'입력예외:{e}')
        for _ in range(15):
            time.sleep(1)
            if _esm_logged_in(d):
                break
    page = d.page_source
    captcha = any(k in page for k in ['자동입력', '캡차', '2차 인증', '추가 인증']) or 'captcha' in page.lower()
    logged = _esm_logged_in(d)
    result = 'OK' if (logged and not captcha) else ('CAPTCHA' if captcha else 'FAIL')
    log(f'결과: LOGGED_IN={logged} CAPTCHA={captcha} → {result} | url={d.current_url[:45]}')
finally:
    log(f'RESULT={result}')
    try: d.quit()
    except Exception: pass
    try: stop_display()
    except Exception: pass
