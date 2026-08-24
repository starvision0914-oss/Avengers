"""지마켓 확인필요(역마진) 상품의 판매가를 예비상품 마켓가(purchase_cost)로 맞춤.
(2026-08-24) 판매중지(gmarket_loss_delete._api_suspend_products)와 같은 API 직접호출 패턴.
가격변경 API는 판매중지 API와 요청 형태가 달라 별도로 실측 확인함(헤더가 아니라 body 안에
siteSellerId가 들어가고, 키도 price가 아니라 request):
  PUT /api/ea/goods/{goods_no}/price
  body: {"request": {"gmkt": 새가격}, "siteSellerId": {"gmkt": 셀러ID, "iac": 셀러ID}}
동일가 no-op 테스트로 실제 검증 완료(2026-08-24).
"""
import json
import time

from .gmarket_loss_delete import _log, _lookup_goods_by_pno

_SET_PRICE_JS = (
    "var cb=arguments[arguments.length-1];var gid=arguments[0];var market=arguments[1];"
    "var price=arguments[2];var sg=arguments[3];var sa=arguments[4];"
    "var body={request:{},siteSellerId:{gmkt:sg,iac:sa}};body.request[market]=price;"
    "fetch('/api/ea/goods/'+gid+'/price',{method:'PUT',credentials:'include',"
    "headers:{'Content-Type':'application/json'},"
    "body:JSON.stringify(body)})"
    ".then(function(r){return r.text().then(function(t){cb(JSON.stringify({status:r.status,text:t}));});})"
    ".catch(function(e){cb(JSON.stringify({status:0,text:String(e)}));});"
)


def _api_update_prices(driver, items, log_fn=None):
    """items: [(product_no, target_price), ...]. 사이트에 반영 성공한 product_no만 반환
    (HTTP 200/204만 성공으로 인정 — 낙관적 가정 금지, gmarket_loss_delete와 동일 원칙)."""
    product_nos = [pno for pno, _ in items]
    info = _lookup_goods_by_pno(driver, product_nos, log_fn)
    price_by_pno = dict(items)
    ok = []
    for pno in product_nos:
        meta = info.get(str(pno))
        if not meta:
            _log(log_fn, f'  ⚠ {pno} 검색 안 됨(삭제됐거나 이미 다른 상태일 수 있음)')
            continue
        target = price_by_pno[pno]
        try:
            txt = driver.execute_async_script(
                _SET_PRICE_JS, meta['goods_no'], meta['market_key'], target,
                meta['seller_g'], meta['seller_a'])
            r = json.loads(txt)
            if r.get('status') in (200, 204):
                ok.append(pno)
            else:
                _log(log_fn, f'  ❌ {pno} 실패 status={r.get("status")} {str(r.get("text",""))[:100]}')
        except Exception as e:
            _log(log_fn, f'  ❌ {pno} 예외: {e}')
        time.sleep(0.5)   # 사람처럼 페이싱(가격변경은 판매중지보다 민감 — 여유있게)
    _log(log_fn, f'  API 가격변경: {len(ok)}/{len(product_nos)}건 성공')
    return ok


def run_price_match(targets, log_fn=None):
    """targets: [{login_id, product_no, target_price}, ...]. 계정별 순차 처리 + 락 1회.
    gmarket_loss_delete.run_delete와 동일 패턴(로그인→iframe→계정별 청크 API호출)."""
    from apps.cpc.models import CrawlerAccount, GmarketMyProduct
    from apps.cpc import eleven_block_guard as guard
    from crawlers.browser import create_driver
    from crawlers.gmarket_cost_crawler import _esm_login
    from crawlers.gmarket_product_crawler import _try_cookie_login, _enter_goods_iframe, _save_cookies

    CHUNK_SIZE = 200

    by_acc = {}
    for t in targets:
        by_acc.setdefault(t['login_id'], []).append(t)

    ok, reason = guard.preflight('지마켓가격맞춤', platform='gmarket', wait=True)
    if not ok:
        _log(log_fn, f'⛔ preflight 차단: {reason}')
        return {'ok': False, 'skipped': reason}
    if reason != 'ok':
        _log(log_fn, f'⏳ 락 대기 후 시작: {reason}')

    summary = {'accounts': 0, 'updated': 0, 'failed': 0}
    results = []
    try:
        for eid, items in by_acc.items():
            pairs = []
            seen = set()
            for t in items:
                p = str(t.get('product_no', '')).strip()
                if p and p not in seen:
                    seen.add(p)
                    pairs.append((p, int(t['target_price'])))
            if not pairs:
                continue
            _log(log_fn, f'[{eid}] 대상 {len(pairs)}개 (판매가→마켓가 맞춤)')
            acc = CrawlerAccount.objects.filter(platform='gmarket', login_id=eid).first()
            if not acc:
                summary['failed'] += 1
                continue
            d = None
            try:
                d = create_driver(kill_existing=False)
                d.set_page_load_timeout(45)
                if not _try_cookie_login(d, acc):
                    if not _esm_login(d, eid, acc.password_enc or ''):
                        _log(log_fn, f'[{eid}] ❌ 로그인 실패(캡차 가능) — 건너뜀')
                        summary['failed'] += 1
                        continue
                    _save_cookies(d, acc)
                else:
                    _log(log_fn, f'[{eid}] 쿠키 로그인 성공(재로그인 생략)')
                if not _enter_goods_iframe(d):
                    _log(log_fn, f'[{eid}] ❌ 상품관리 iframe 진입 실패')
                    summary['failed'] += 1
                    continue

                acc_updated = 0
                acc_fail_chunks = 0
                chunks = [pairs[i:i + CHUNK_SIZE] for i in range(0, len(pairs), CHUNK_SIZE)]
                for ci, chunk in enumerate(chunks, 1):
                    _log(log_fn, f'  [{eid}] 배치 {ci}/{len(chunks)} ({len(chunk)}개)')
                    applied = _api_update_prices(d, chunk, log_fn)
                    if applied:
                        price_by_pno = dict(chunk)
                        # 상품별 목표가가 서로 달라 update()로 일괄 처리 불가 — 건별 업데이트.
                        for pno in applied:
                            GmarketMyProduct.objects.filter(
                                account=acc, product_no=pno).update(sale_price=price_by_pno[pno])
                        acc_updated += len(applied)
                    if len(applied) < len(chunk):
                        acc_fail_chunks += 1

                summary['accounts'] += 1
                summary['updated'] += acc_updated
                results.append({'login_id': eid, 'updated': acc_updated,
                                 'requested': len(pairs), 'failed_batches': acc_fail_chunks})
            finally:
                if d:
                    try:
                        d.quit()
                    except Exception:
                        pass
    finally:
        try:
            guard.release_global_lock(platform='gmarket')
        except Exception:
            pass

    summary['results'] = results
    return {'ok': True, **summary}
