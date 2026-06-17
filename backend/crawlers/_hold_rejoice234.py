"""rejoice234 ESM 로그인 후 판매예치금 페이지에서 세션 유지(대기)."""
import os, time, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from crawlers.browser import create_driver
from crawlers.gmarket_cost_crawler import _try_cookie_login, _esm_login
from apps.cpc.models import CrawlerAccount

acc = CrawlerAccount.objects.get(platform='gmarket', login_id='rejoice234')
d = create_driver(kill_existing=False)
SHOT = '/tmp/rejoice234_session.png'
try:
    if _try_cookie_login(d, acc):
        print('쿠키 로그인 성공', flush=True)
    elif _esm_login(d, 'rejoice234', acc.password_enc):
        print('풀로그인 성공', flush=True)
    else:
        print('로그인 실패', flush=True)
    d.get('https://www.esmplus.com/Member/Settle/GmktSellBalanceManagement')
    time.sleep(4)
    print('현재 URL:', d.current_url, flush=True)
    try:
        d.save_screenshot(SHOT)
        print('스크린샷 저장:', SHOT, flush=True)
    except Exception as e:
        print('스크린샷 실패:', e, flush=True)
    print('=== 로그인 상태로 대기 시작 (세션 유지) ===', flush=True)
    # 세션 유지 — 최대 40분, 5분마다 keep-alive
    for i in range(8):
        time.sleep(300)
        try:
            _ = d.current_url  # keep-alive
            print(f'[keep-alive {i+1}] url={d.current_url[:50]}', flush=True)
        except Exception as e:
            print('세션 끊김:', e, flush=True); break
finally:
    try: d.quit()
    except Exception: pass
print('=== 대기 종료 ===', flush=True)
