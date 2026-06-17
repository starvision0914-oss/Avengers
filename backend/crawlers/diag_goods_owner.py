"""진단: ESM goods/search item에서 '소유 판매자ID' 필드 찾기.
공유ESM(rejoice222=222/223/224)에서 각 상품이 어느 G마켓 id 소유인지 식별할 키를 탐색.
읽기전용: 1페이지(500건)만 조회, DB 미저장."""
import json
import time

from crawlers.gmarket_product_crawler import (
    _try_cookie_login, _esm_login, _enter_goods_iframe, _SEARCH_JS,
)


def run(login_id='rejoice222', log_fn=print):
    from apps.cpc.models import CrawlerAccount
    from apps.cpc import eleven_block_guard as guard
    from crawlers.browser import create_driver, stop_display

    a = CrawlerAccount.objects.get(platform='gmarket', login_id=login_id)
    ok, reason = guard.preflight('상품소유진단', platform='gmarket')
    if not ok:
        log_fn(f'⏭️ 건너뜀 — {reason}')
        return
    driver = None
    try:
        driver = create_driver(kill_existing=False)
        driver.delete_all_cookies()
        if _try_cookie_login(driver, a):
            log_fn(f'[{login_id}] 쿠키 로그인')
        elif _esm_login(driver, login_id, a.password_enc):
            log_fn(f'[{login_id}] 풀 로그인')
        else:
            log_fn(f'[{login_id}] 로그인 실패'); return
        if not _enter_goods_iframe(driver):
            log_fn('iframe 진입 실패'); return
        txt = driver.execute_async_script(_SEARCH_JS, 1, 500)
        driver.switch_to.default_content()
        data = json.loads(txt).get('data') or {}
        items = data.get('items') or []
        log_fn(f'총 조회 {len(items)}건, data 최상위 키: {list(json.loads(txt).get("data",{}).keys())}')
        if not items:
            return
        it = items[0]
        log_fn('\n=== item[0] 전체 키 ===')
        log_fn(', '.join(it.keys()))
        log_fn('\n=== item[0] 전체 JSON ===')
        log_fn(json.dumps(it, ensure_ascii=False, indent=1)[:3000])
        # 소유자 후보 필드 탐색: 값에 222/223/224가 들어있는 키
        log_fn('\n=== 소유자 후보(값에 sub id 포함된 필드) ===')
        subs = ['rejoice222', 'rejoice223', 'rejoice224', '222', '223', '224']
        def scan(o, path=''):
            hits = []
            if isinstance(o, dict):
                for k, v in o.items():
                    hits += scan(v, f'{path}.{k}')
            elif isinstance(o, list):
                for i, v in enumerate(o[:3]):
                    hits += scan(v, f'{path}[{i}]')
            else:
                s = str(o)
                if any(x == s or x in s for x in subs):
                    hits.append((path, s))
            return hits
        seen = set()
        for itx in items[:50]:
            for p, v in scan(itx):
                if p not in seen:
                    seen.add(p)
                    log_fn(f'  {p} = {v}')
        # siteGoodsNo 구조와 분포
        log_fn('\n=== siteGoodsNo 샘플 5건 ===')
        for itx in items[:5]:
            log_fn(f'  {json.dumps(itx.get("siteGoodsNo"), ensure_ascii=False)}')
    finally:
        try:
            if driver: driver.quit()
        except Exception:
            pass
        guard.release_global_lock(platform='gmarket')
        try:
            stop_display()
        except Exception:
            pass
