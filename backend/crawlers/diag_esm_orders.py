"""ESM 주문/배송/정산관리 엔드포인트 캡처 — 읽기전용(주문 변경 없음).
기존 ESM PLUS 로그인(gmarket_product_crawler) 재사용 → Home/v2 네비 메뉴 링크 덤프 +
주문/배송관리 후보 페이지의 iframe src + 호출된 /api XHR 엔드포인트(performance) 수집.
실행: /usr/bin/python3 crawlers/diag_esm_orders.py [login_id]
목적: 주문상태(배송중/구매확정/정산지연 등) 직접크롤용 엔드포인트 식별. 어떤 클릭/저장도 안 함."""
import os, sys, time, json, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from apps.cpc.models import CrawlerAccount
from apps.cpc import eleven_block_guard as guard
from crawlers.browser import create_driver, stop_display
from crawlers.gmarket_product_crawler import _try_cookie_login, _esm_login, _save_cookies
from selenium.webdriver.common.by import By

KEYS = ('주문', '배송', '발송', '구매확정', '정산', '클레임', '교환', '반품', '취소',
        'order', 'delivery', 'claim', 'deal', 'settle', 'sell')
# 시도할 주문/배송 후보 URL (상품=goods-manage 패턴에서 유추 — 실제 도달여부로 검증)
CANDIDATES = [
    'https://www.esmplus.com/Home/v2/delivery-manage',
    'https://www.esmplus.com/Home/v2/order-manage',
    'https://www.esmplus.com/Home/v2/order',
    'https://www.esmplus.com/Home/v2/claim-manage',
    'https://www.esmplus.com/Home/v2/settle-manage',
]


def log(m):
    print(m, flush=True)


def dump_apis(driver, label):
    try:
        urls = driver.execute_script(
            "return (performance.getEntriesByType('resource')||[]).map(function(e){return e.name;});")
    except Exception as e:
        log(f'  [{label}] perf 오류 {e}'); return
    hits = [u for u in urls if any(k in u.lower() for k in
            ('/api', 'order', 'delivery', 'claim', 'deal', 'settle', 'ship'))]
    hits = list(dict.fromkeys(hits))
    log(f'  [{label}] XHR/API 후보 {len(hits)}개:')
    for u in hits[:30]:
        log(f'     {u[:160]}')


def main():
    eid = sys.argv[1] if len(sys.argv) > 1 else 'dlrmsgh012'
    a = CrawlerAccount.objects.filter(platform='gmarket', login_id=eid).first()
    if not a:
        log(f'계정 {eid} 없음'); return

    ok, reason = guard.preflight('ESM주문캡처', platform='gmarket')
    if not ok:
        log(f'⏭️ 건너뜀 — {reason}'); return

    driver = None
    try:
        driver = create_driver(kill_existing=False)
        t = time.time()
        if _try_cookie_login(driver, a):
            log(f'쿠키 로그인 OK {time.time()-t:.1f}s')
        elif _esm_login(driver, a.login_id, a.password_enc):
            log(f'풀 로그인 OK {time.time()-t:.1f}s')
            _save_cookies(driver, a)
        else:
            log('로그인 실패'); return

        # 1) Home/v2 네비 메뉴 링크 덤프 (주문/배송/정산 메뉴 URL 찾기)
        driver.get('https://www.esmplus.com/Home/v2')
        time.sleep(6)
        log(f'현재 URL: {driver.current_url}')
        links = driver.find_elements(By.XPATH, "//a[@href]")
        seen = set(); found = []
        for el in links:
            href = el.get_attribute('href') or ''
            txt = (el.text or '').strip()
            blob = (href + ' ' + txt).lower()
            if any(k.lower() in blob for k in KEYS) and href not in seen:
                seen.add(href); found.append((txt[:24], href))
        log(f'=== 네비 링크(주문/배송/정산 관련) {len(found)}개 ===')
        for txt, href in found[:40]:
            log(f'   "{txt}"  →  {href[:120]}')

        # 2) 후보 URL 도달성 + iframe + API 덤프 (읽기전용)
        targets = [h for _, h in found if any(k in h.lower() for k in
                   ('order', 'delivery', 'claim', 'settle', '주문', '배송', '정산'))][:4]
        targets = list(dict.fromkeys(targets + CANDIDATES))
        for url in targets[:7]:
            try:
                driver.get(url)
                time.sleep(7)
                cur = driver.current_url
                redirected = ('login' in cur.lower() or 'signin' in cur.lower())
                log(f'\n--- {url}')
                log(f'   도달 URL: {cur[:120]}  title="{(driver.title or "")[:30]}"  '
                    f'{"⚠️로그인페이지로 튕김" if redirected else "OK"}')
                ifr = [f.get_attribute('src') for f in driver.find_elements(By.TAG_NAME, 'iframe')]
                ifr = [s for s in ifr if s]
                log(f'   iframe {len(ifr)}개: ' + '; '.join(s[:90] for s in ifr[:5]))
                dump_apis(driver, 'apis')
            except Exception as e:
                log(f'   {url} 오류 {str(e)[:80]}')

        log('\n=== 캡처 완료 (주문/데이터 변경 없음, 읽기전용) ===')
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        guard.release_global_lock(platform='gmarket')
        try:
            stop_display()
        except Exception:
            pass


if __name__ == '__main__':
    main()
