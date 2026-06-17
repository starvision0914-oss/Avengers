"""rejoice666(지마켓) 로그인 보안화면 진단 — 1회만 시도, 스크린샷+제목+URL+키워드 추출."""
import os, sys, time, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from selenium.webdriver.common.by import By
from crawlers.browser import create_driver, stop_display
from crawlers.gmarket_cost_crawler import _esm_logged_in, _dismiss_esm_popups
from apps.cpc.models import CrawlerAccount

a = CrawlerAccount.objects.get(login_id='rejoice666', platform='gmarket')
SHOT = '/tmp/gmkt666_security.png'
d = create_driver()
try:
    d.get('https://www.esmplus.com/')
    time.sleep(3)
    if not _esm_logged_in(d):
        for b in d.find_elements(By.XPATH, "//button[contains(@class,'button__tab')]"):
            if (b.text or '').strip() == '지마켓':
                d.execute_script("arguments[0].click();", b); time.sleep(1); break
        try:
            idf = d.find_element(By.ID, 'typeMemberInputId01')
            pwf = d.find_element(By.ID, 'typeMemberInputPassword01')
            idf.clear(); idf.send_keys(a.login_id)
            pwf.clear(); pwf.send_keys(a.password_enc)
            d.find_element(By.XPATH, "//button[contains(@class,'button--blue') and contains(.,'로그인')]").click()
        except Exception as e:
            print('입력단계 예외:', e)
        # 로그인 후 화면 안정화 대기(인증게이트 렌더 시간)
        for _ in range(12):
            time.sleep(1)
            if _esm_logged_in(d):
                break
    d.save_screenshot(SHOT)
    url = d.current_url
    title = d.title
    body = (d.find_element(By.TAG_NAME, 'body').text or '')[:1500]
    print('=== URL ===', url)
    print('=== TITLE ===', title)
    print('=== LOGGED_IN ===', _esm_logged_in(d))
    KW = ['보안', '추가 인증', '추가인증', '본인인증', '인증번호', '휴대폰', '문자', '이메일',
          '이상', '차단', '비정상', '안전', '캡차', '자동입력', '재설정', '비밀번호',
          '잠금', '일시', 'OTP', '2단계', '간편']
    hit = [k for k in KW if k in body]
    print('=== 키워드 감지 ===', hit)
    print('=== BODY(앞 1500자) ===')
    print(body)
    print('=== SCREENSHOT ===', SHOT)
finally:
    try: d.quit()
    except Exception: pass
    stop_display()
