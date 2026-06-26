"""지마켓/옥션(ESM) 나의 상품 수집 — item.esmplus.com 상품검색 API.

흐름(라이브 검증 2026-06-10, dlrmsgh012 = 지마켓 15,140 + 옥션 4,017):
  1. signin.esmplus.com 로그인 (지마켓 탭). 쿠키 재사용으로 중복세션 방지.
  2. www.esmplus.com/Home/v2/goods-manage 진입 → iframe(item.esmplus.com) 컨텍스트로 전환
  3. POST /api/ea/goods/search 를 pageIndex 증가시키며 호출(같은 origin fetch) → 전체 상품 수집
  4. 각 상품의 site별(gmkt/iac) 상품번호로 GmarketMyProduct upsert
     (account+market+상품번호 유니크 = 중복제거, 누적)

안전: eleven_block_guard 통합 락(preflight).
"""
import json
import logging
import time

from django.utils import timezone

logger = logging.getLogger('crawler')

GOODS_MANAGE = 'https://www.esmplus.com/Home/v2/goods-manage'
PAGE_SIZE = 500
# ESM EA sellStatus 코드 → 라벨 (확인된 것만; 미확인은 코드 그대로)
SELL_STATUS = {'11': '판매중', '21': '판매중', '22': '판매중지', '23': '품절', '24': '판매종료', '25': '판매불가'}

# 같은 origin(iframe=item.esmplus.com)에서 상품검색 API 호출
# sellStatus 인자(3번째): JS 배열 문자열 — [] = 판매중(11,21), [22] = 판매중지, [25] = 판매불가
_SEARCH_JS = (
    "var cb=arguments[arguments.length-1];var idx=arguments[0];var size=arguments[1];var ss=arguments[2]||[];"
    "fetch('/api/ea/goods/search',{method:'POST',credentials:'include',"
    "headers:{'Content-Type':'application/json'},"
    "body:JSON.stringify({query:{goodsIds:'',keyword:'',sellStatus:ss,category:{},"
    "registrationDate:{},shipping:{},additionalService:[]},pageIndex:idx,pageSize:size})})"
    ".then(function(r){return r.text();}).then(function(t){cb(t);}).catch(function(e){cb('ERR:'+e);});"
)


def _log(log_fn, m):
    logger.info(m)
    if log_fn:
        log_fn(m)


COOKIE_TTL_HOURS = 72   # 쿠키 재사용 TTL — 유효 쿠키면 로그인 생략(속도↑, 로그인부하↓=IP안전)


def _try_cookie_login(driver, account):
    """저장 쿠키로 빠른 로그인. esmplus 도달(로그인페이지 아님) 확인. 실패 시 False→풀로그인 폴백."""
    import json
    from datetime import timedelta
    from django.utils import timezone
    if not account.cookie_data or not account.cookie_saved_at:
        return False
    if timezone.now() - account.cookie_saved_at > timedelta(hours=COOKIE_TTL_HOURS):
        return False
    try:
        driver.get('https://www.esmplus.com/')
        time.sleep(1)
        for c in json.loads(account.cookie_data):
            c.pop('sameSite', None)
            c.pop('expiry', None)
            try:
                driver.add_cookie(c)
            except Exception:
                pass
        driver.get('https://www.esmplus.com/Home/v2')
        time.sleep(2)
        u = driver.current_url.lower()
        return ('login' not in u and 'signin' not in u)
    except Exception:
        return False


def _save_cookies(driver, account):
    import json
    from django.utils import timezone
    try:
        account.cookie_data = json.dumps(driver.get_cookies())
        account.cookie_saved_at = timezone.now()
        account.save(update_fields=['cookie_data', 'cookie_saved_at'])
    except Exception:
        pass


def _esm_login(driver, eid, pw):
    """ESM Plus 본포털 로그인 (지마켓 탭). 이미 로그인 상태면 통과."""
    from selenium.webdriver.common.by import By
    driver.get('https://www.esmplus.com/')
    time.sleep(3)
    if 'login' not in driver.current_url.lower() and 'signin' not in driver.current_url.lower():
        return True
    for b in driver.find_elements(By.XPATH, "//button[contains(@class,'button__tab')]"):
        if (b.text or '').strip() == '지마켓':
            driver.execute_script("arguments[0].click();", b)
            time.sleep(1)
            break
    driver.find_element(By.ID, 'typeMemberInputId01').send_keys(eid)
    driver.find_element(By.ID, 'typeMemberInputPassword01').send_keys(pw)
    driver.find_element(By.XPATH, "//button[contains(@class,'button--blue') and contains(.,'로그인')]").click()
    time.sleep(6)
    return 'login' not in driver.current_url.lower() and 'signin' not in driver.current_url.lower()


def _enter_goods_iframe(driver):
    """goods-manage 진입 후 item.esmplus.com iframe 컨텍스트로 전환."""
    from selenium.webdriver.common.by import By
    driver.get(GOODS_MANAGE)
    time.sleep(8)
    frames = driver.find_elements(By.TAG_NAME, 'iframe')
    for f in frames:
        if 'item.esmplus.com' in (f.get_attribute('src') or ''):
            driver.switch_to.frame(f)
            time.sleep(2)
            return True
    if frames:
        driver.switch_to.frame(frames[0])
        time.sleep(2)
        return True
    return False


def _fetch_goods_by_status(driver, eid, log_fn, sell_status_filter):
    """sellStatus 필터별 상품 페이징 수집. sell_status_filter: [] = 판매중, [22] = 판매중지, [25] = 판매불가."""
    items = []
    page = 1
    while page <= 500:
        txt = driver.execute_async_script(_SEARCH_JS, page, PAGE_SIZE, sell_status_filter)
        if not txt or txt.startswith('ERR:'):
            _log(log_fn, f'[{eid}] API 오류 p{page} filter={sell_status_filter}: {str(txt)[:80]}')
            break
        try:
            data = json.loads(txt).get('data') or {}
        except Exception:
            _log(log_fn, f'[{eid}] JSON 파싱 실패 p{page}')
            break
        batch = data.get('items') or []
        if not batch:
            break
        items.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        page += 1
        time.sleep(0.6)
    return items


def _fetch_all_goods(driver, eid, log_fn):
    """판매중 + 판매중지(22) + 판매불가(25) 를 각각 쿼리해 합산 반환.
    sellStatus:[] = 판매중(11,21)만 반환, 판매중지/판매불가는 별도 쿼리 필요."""
    # 판매중 (기본)
    items = _fetch_goods_by_status(driver, eid, log_fn, [])
    _log(log_fn, f'[{eid}] 판매중: {len(items)}개')

    # 판매중지 (22) — 판매자가 직접 중지, 소수 예상
    paused = _fetch_goods_by_status(driver, eid, log_fn, [22])
    _log(log_fn, f'[{eid}] 판매중지: {len(paused)}개')
    items.extend(paused)

    # 판매불가 (25) — 플랫폼 차단, 계정당 20-30개 예상
    unavail = _fetch_goods_by_status(driver, eid, log_fn, [25])
    _log(log_fn, f'[{eid}] 판매불가: {len(unavail)}개')
    items.extend(unavail)

    _log(log_fn, f'[{eid}] 전체: {len(items)}개')
    return items


def _owner_map(account):
    """공유ESM 그룹의 모든 판매자 id(login_id) → CrawlerAccount.
    item.siteSellerId(gmkt/iac)로 각 상품을 실제 소유 계정에 귀속하기 위한 매핑.
    (공유ESM은 한 로그인이 그룹 전체 상품을 반환 → 소유자별로 분배 저장)"""
    from django.db.models import Q
    from apps.cpc.models import CrawlerAccount
    origin = account.gmarket_origin_id or account.login_id
    m = {}
    for c in CrawlerAccount.objects.filter(platform='gmarket').filter(
            Q(login_id=origin) | Q(gmarket_origin_id=origin)):
        m[c.login_id] = c
    m.setdefault(account.login_id, account)
    return m


def _save_items(account, items):
    """상품 items → GmarketMyProduct 누적 upsert(bulk). 한 상품이 지마켓/옥션 동시면 각각 1행.
    각 상품은 item.siteSellerId[site]가 가리키는 실제 소유 판매자id 계정에 귀속(공유ESM 분배).
    매핑 없으면 로그인 계정으로 폴백. bulk_create + update_conflicts 로 수만 건도 빠르게 처리."""
    from apps.cpc.models import GmarketMyProduct
    now = timezone.now()
    acc_by_lid = _owner_map(account)
    objs = []
    seen = set()
    for it in items:
        site_no = it.get('siteGoodsNo') or {}
        site_seller = it.get('siteSellerId') or {}
        price = it.get('price') or {}
        stock = it.get('stock') or {}
        sell = it.get('sellStatus') or {}
        cat = (((it.get('category') or {}).get('esm') or {}).get('catName') or '')[:50]
        name = (it.get('goodsName') or '')[:500]
        code = (it.get('managedCode') or '')[:100]
        for site, market in (('gmkt', 'gmarket'), ('iac', 'auction')):
            pno = site_no.get(site)
            if not pno:
                continue
            pno = str(pno)
            owner = acc_by_lid.get(site_seller.get(site)) or account
            key = (owner.login_id, market, pno)
            if key in seen:
                continue
            seen.add(key)
            st = sell.get(site)
            st = SELL_STATUS.get(str(st), str(st) if st is not None else '')
            objs.append(GmarketMyProduct(
                account=owner, market=market, product_no=pno,
                product_name=name, seller_product_code=code,
                sale_price=int(price.get(site) or 0),
                stock_quantity=int(stock.get(site) or 0),
                status_type=st[:20], category_code=cat, synced_at=now))
    if objs:
        # MySQL/MariaDB: update_conflicts=True 사용하되 unique_fields는 지정 불가
        # (기존 unique_together 인덱스로 ON DUPLICATE KEY UPDATE 동작)
        GmarketMyProduct.objects.bulk_create(
            objs, update_conflicts=True,
            update_fields=['product_name', 'seller_product_code', 'sale_price',
                           'stock_quantity', 'status_type', 'category_code', 'synced_at'],
            batch_size=1000)
    return len(objs)


def run_all_accounts(log_fn=None, account_filter=None):
    """활성 지마켓 계정의 ESM 상품을 API로 전량 수집해 GmarketMyProduct에 누적."""
    from apps.cpc.models import CrawlerAccount
    from apps.cpc import eleven_block_guard as guard
    from crawlers.browser import create_driver, stop_display

    ok, reason = guard.preflight('지마켓상품수집', platform='gmarket')
    if not ok:
        _log(log_fn, f'⏭️ 지마켓 상품수집 건너뜀 — {reason}')
        return {'ok': False, 'skipped': reason}

    qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True)
    accounts = [a for a in qs if (not account_filter or a.login_id in account_filter)]
    # 공유ESM 서브계정(gmarket_origin_id 보유)은 마스터 크롤이 siteSellerId로 함께 수집 →
    # 명시 필터가 없으면 서브 스킵(중복 로그인/IP노출 방지). 마스터만 돌면 그룹 전체 분배됨.
    if not account_filter:
        accounts = [a for a in accounts
                    if not (a.gmarket_origin_id and a.gmarket_origin_id != a.login_id)]
    done = failed = total_items = 0
    driver = None
    try:
        for a in accounts:
            blocked, _, _ = guard.is_blocked(platform='gmarket')
            if blocked:
                _log(log_fn, '⛔ 차단 감지 — 중단')
                break
            _log(log_fn, f'[{a.login_id}] ESM 로그인...')
            try:
                if driver is None:
                    driver = create_driver(kill_existing=False)
                driver.delete_all_cookies()
                # 쿠키 재사용 우선 → 실패 시 풀로그인 후 쿠키 저장(IP안전+속도)
                if _try_cookie_login(driver, a):
                    _log(log_fn, f'[{a.login_id}] 쿠키 로그인')
                else:
                    if not _esm_login(driver, a.login_id, a.password_enc):
                        _log(log_fn, f'[{a.login_id}] 로그인 실패 — 건너뜀')
                        failed += 1
                        continue
                    _save_cookies(driver, a)
                try:
                    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': 'window.__x=1;'})
                except Exception:
                    pass
                if not _enter_goods_iframe(driver):
                    _log(log_fn, f'[{a.login_id}] 상품 iframe 진입 실패')
                    failed += 1
                    continue
                items = _fetch_all_goods(driver, a.login_id, log_fn)
                driver.switch_to.default_content()
                n = _save_items(a, items)
                total_items += n
                done += 1
                _log(log_fn, f'[{a.login_id}] 상품 {len(items)}건 조회 → {n}행 저장(누적)')
            except Exception as e:
                _log(log_fn, f'[{a.login_id}] 오류: {str(e)[:140]}')
                failed += 1
                try:
                    driver.switch_to.default_content()
                except Exception:
                    pass
            time.sleep(3)
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
        guard.release_global_lock(platform='gmarket')
        try:
            stop_display()
        except Exception:
            pass
    _log(log_fn, f'🛒 [지마켓 상품수집 완료] 계정 {done} / 저장 {total_items}행 / 실패 {failed}')
    return {'ok': True, 'accounts': done, 'items': total_items, 'failed': failed}
