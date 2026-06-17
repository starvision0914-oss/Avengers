"""지마켓 쿠키 로그인 프로브 — 자격증명 제출 없이 저장 쿠키가 유효한지만 확인(캡차 미유발).
사용: python3 -u probe_gmkt_cookie.py [login_id1 login_id2 ...]  (기본 3계정)"""
import os, sys, time, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from crawlers.browser import create_driver, stop_display
from crawlers.gmarket_cost_crawler import _try_cookie_login, _esm_logged_in
from apps.cpc.models import CrawlerAccount

IDS = sys.argv[1:] or list(CrawlerAccount.objects.filter(
    platform='gmarket', is_active=True).order_by('login_id').values_list('login_id', flat=True)[:3])

d = create_driver(kill_existing=False)
try:
    for lid in IDS:
        a = CrawlerAccount.objects.filter(login_id=lid, platform='gmarket').first()
        if not a:
            print(f'{lid}: 계정없음'); continue
        try:
            ok = _try_cookie_login(d, a)
        except Exception as e:
            ok = False; print(f'{lid}: 예외 {e}')
        print(f'{lid}: 쿠키로그인 {"성공(유효)" if ok else "실패(무효→풀로그인 필요=캡차위험)"} | url={d.current_url[:50]}', flush=True)
        d.delete_all_cookies()
finally:
    try: d.quit()
    except Exception: pass
    stop_display()
