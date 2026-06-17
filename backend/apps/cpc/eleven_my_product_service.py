import logging
import os
import random
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from django.db.models import Max
from django.utils import timezone

from .models import CrawlerAccount, ElevenMyProduct
from . import eleven_block_guard as guard

logger = logging.getLogger(__name__)

ELEVEN_API_URL = 'https://openapi.11st.co.kr/openapi/OpenApiService.tmall'

# 11번가 OpenAPI 차단 회피 — 매우 보수적인 페이싱
# (2026-05-25 ConnectTimeout 차단 경험 반영 — 페이싱 50% ↑)
PAGE_SLEEP = (8.0, 12.0)       # 페이지 간 8~12초 (적정선)
ACCOUNT_SLEEP = (50.0, 70.0)   # 계정 간 50~70초 (적정선)
MAX_RETRIES = 3                # 일시적 ConnectTimeout 자동 재시도 (2 → 3)
SOFT_FAIL_THRESHOLD = 3        # 연속 실패 N회 → circuit breaker 발동
RECOVERY_WAIT = (60.0, 120.0)  # ConnectTimeout 후 회복 대기 (신규)
RECENT_SYNC_HOURS = 6          # N시간 내 성공한 계정은 스킵

# 셀러 도구 류 트래픽으로 위장 (일반 브라우저 UA)
_BROWSER_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/131.0.0.0 Safari/537.36'
)


def _make_session():
    s = requests.Session()
    s.headers.update({
        'User-Agent': _BROWSER_UA,
        'Accept': 'application/xml,text/xml,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.5',
        'Connection': 'keep-alive',
    })
    return s


def _fetch_products_page(session, api_key, page_num=1, page_size=100):
    """페이지 1개 조회.
    - 글로벌 차단 락 확인 → 차단 중이면 즉시 RuntimeError
    - 429/503 받으면 글로벌 락 60분 + 즉시 raise (재시도하지 않음 — 차단 신호니까)
    - 일시적 연결 오류는 짧은 재시도 (MAX_RETRIES=2)"""
    guard.guard_or_raise('OpenAPI')
    params = {
        'key': api_key,
        'apiCode': 'ProductSearch',
        'keyword': '',
        'pageNum': page_num,
        'pageSize': page_size,
    }
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(ELEVEN_API_URL, params=params, timeout=30)
            if resp.status_code in (429, 503, 502, 504):
                guard.report_signal(resp.status_code, source='OpenAPI')
                raise RuntimeError(f'11st OpenAPI 차단 신호 HTTP {resp.status_code}')
            resp.raise_for_status()
            return resp.text
        except (requests.ConnectionError, requests.Timeout) as e:
            last_err = e
            if attempt == MAX_RETRIES - 1:
                # 최종 실패 — 글로벌 차단 락 발동
                guard.report_signal(e, source='OpenAPI')
                raise
            # 지수 백오프 + recovery jitter (60~120초 큰 대기 추가)
            base = (2 ** attempt) + random.uniform(1, 3)
            if attempt >= 1:
                base += random.uniform(*RECOVERY_WAIT)  # 2회차 이상 큰 대기
            logger.warning('11st API 연결 오류 (%s) — %.1fs 후 재시도 (%d/%d)',
                           type(e).__name__, base, attempt + 1, MAX_RETRIES)
            time.sleep(base)
    raise last_err or RuntimeError('11st API 호출 실패')


# 안전장치: openapi ProductSearch(apiCode=ProductSearch)는 원래 '셀러 본인 상품'이 아니라
# 11번가 전체 공개 카탈로그(buyer 검색, TotalCount 수억)를 반환한다 → 셀러 상품번호/판매상태가
# 없어 0건 파싱되고, '짧은 페이지' 종료조건이 영영 안 걸려 무한 페이징(락 점유+차단)에 빠진다.
# 이를 감지해 즉시 중단한다. (셀러 상품 정식 경로는 셀러오피스 product-list JSON API)
PRODUCTSEARCH_MAX_PAGES = 500          # 하드 상한 (셀러 한 명이 5만개 이상일 일은 없음)
SELLER_TOTALCOUNT_SANITY = 1_000_000   # TotalCount가 이보다 크면 buyer 카탈로그로 간주


def fetch_all_products_from_eleven(api_key, log_fn=None, session=None):
    all_products = []
    page = 1
    page_size = 100
    sess = session or _make_session()

    while True:
        if log_fn:
            log_fn(f'page {page} 조회 중...')
        xml_text = _fetch_products_page(sess, api_key, page, page_size)
        soup = BeautifulSoup(xml_text, 'lxml-xml')

        products = soup.find_all('Product')
        if not products:
            break

        page_valid = 0
        for p in products:
            def _text(tag_name):
                tag = p.find(tag_name)
                return tag.get_text(strip=True) if tag else ''

            product_no_str = _text('ProductNo') or _text('PrdNo')
            if not product_no_str:
                continue
            try:
                product_no = int(product_no_str)
            except ValueError:
                continue
            page_valid += 1

            try:
                sale_price = int(_text('SalePrice') or _text('SelPrc') or 0)
            except ValueError:
                sale_price = 0
            try:
                stock = int(_text('StockQty') or _text('PrdStckQty') or 0)
            except ValueError:
                stock = 0

            all_products.append({
                'product_no': product_no,
                'product_name': (_text('ProductName') or _text('PrdNm'))[:500],
                'sale_price': sale_price,
                'stock_quantity': stock,
                'status_type': _text('SelStatCd') or _text('SaleStatusCode') or _text('ProductStatusCode'),
                'seller_product_code': _text('SellerPrdCd') or _text('SellerProductCode'),
                'category_id': _text('DispCtgrNo') or _text('CategoryCode'),
                'product_image_url': _text('PrdImage01') or _text('ProductImage'),
            })

        total_count_tag = soup.find('TotalCount')
        try:
            total_count = int(total_count_tag.get_text(strip=True)) if total_count_tag else 0
        except ValueError:
            total_count = 0

        # buyer 카탈로그 감지(첫 페이지) — 셀러 상품이 한 건도 파싱 안 되거나 TotalCount가
        # 비정상적으로 크면 ProductSearch가 셀러 API가 아닌 것 → 무한페이징 전에 즉시 중단.
        if page == 1 and (page_valid == 0 or total_count > SELLER_TOTALCOUNT_SANITY):
            raise RuntimeError(
                f'ProductSearch가 셀러 상품을 반환하지 않음(파싱 {page_valid}건, TotalCount={total_count}) '
                f'— buyer 전체검색 API. 셀러오피스 product-list 경로 필요.')

        if page * page_size >= total_count or len(products) < page_size:
            break
        if page >= PRODUCTSEARCH_MAX_PAGES:
            if log_fn:
                log_fn(f'⚠️ 페이지 상한 {PRODUCTSEARCH_MAX_PAGES} 도달 — 중단(무한페이징 방지)')
            break
        page += 1
        time.sleep(random.uniform(*PAGE_SLEEP))

    return all_products


def sync_products_for_account(account_id, log_fn=None, session=None, allow_selenium_fallback=False):
    """11번가 단일 계정 상품 동기화 (OpenAPI 전용).

    allow_selenium_fallback=True 로 명시 호출 시에만 Selenium 폴백(크롤러)을 시도한다.
    기본값은 False — api_key 없는 계정은 그냥 에러 반환.
    (운영 정책: api_key 보유 계정만 크롤링 대상)
    """
    try:
        account = CrawlerAccount.objects.get(pk=account_id, platform='11st')
    except CrawlerAccount.DoesNotExist:
        return {'error': '11번가 계정을 찾을 수 없습니다.', 'account_id': account_id}

    if not account.api_key:
        if not allow_selenium_fallback:
            return {'error': 'API 키가 등록되지 않았습니다.', 'login_id': account.login_id, 'synced': 0}
        # 명시 요청 시에만 Selenium 폴백 (운영상 기본 OFF)
        if log_fn:
            log_fn(f'[{account.login_id}] api_key 없음 → Selenium 폴백 (명시 요청)')
        from crawlers.eleven_product_crawler import run_all_accounts as _selenium_run
        sel = _selenium_run(
            log_fn=log_fn,
            account_filter=[account.login_id],
            only_no_api_key=False,
        )
        return {
            'login_id': account.login_id,
            'seller_name': account.seller_name,
            'synced': sel.get('collected', 0),
            'failed': sel.get('failed', 0),
            'via': 'selenium',
            'aborted_due_to_block': sel.get('aborted_due_to_block', False),
        }

    try:
        products = fetch_all_products_from_eleven(account.api_key, log_fn=log_fn, session=session)
    except Exception as e:
        logger.exception('11st API error for account %s', account_id)
        return {'error': f'11번가 API 오류: {str(e)}', 'login_id': account.login_id, 'synced': 0}

    now = timezone.now()
    upserted = 0
    for p in products:
        ElevenMyProduct.objects.update_or_create(
            account=account, product_no=p['product_no'],
            defaults={
                'product_name': p['product_name'],
                'sale_price': p['sale_price'],
                'stock_quantity': p['stock_quantity'],
                'status_type': p['status_type'],
                'seller_product_code': p['seller_product_code'],
                'category_id': p['category_id'],
                'product_image_url': p['product_image_url'],
                'synced_at': now,
            },
        )
        upserted += 1

    return {
        'login_id': account.login_id,
        'seller_name': account.seller_name,
        'synced': upserted,
        'total_from_api': len(products),
        'synced_at': now.isoformat(),
    }


def sync_focused_accounts(log_fn=None, fail_fast_threshold=SOFT_FAIL_THRESHOLD,
                          skip_recent=True, force=False, focused_only=True):
    """11번가 나의상품(상태) 일괄 동기화.
    - focused_only=True: 집중관리(is_focused) 계정만. False: api_key 보유 전체 계정.
    - 글로벌 차단 락 활성화 시 즉시 중단
    - skip_recent=True 면 RECENT_SYNC_HOURS 시간 내 동기화 성공 계정 스킵
    - 연속 실패 fail_fast_threshold회 이상이면 자동 글로벌 락 + 중단
    - 영구정지 계정은 제외(API 실패 방지)"""
    # 0) 사전점검: 차단/접속불가/다른 크롤 동시실행 금지 (전역 단일 크롤 — IP 차단 방지)
    _pf_ok, _pf_reason = guard.preflight('나의상품동기화')
    if not _pf_ok:
        blocked, remaining, until = guard.is_blocked()
        return {
            'accounts': [],
            'aborted_due_to_global_block': True,
            'block_remaining_seconds': remaining,
            'block_until': until.isoformat() if until else None,
            'message': f'동시 크롤/차단으로 스킵 — {_pf_reason}',
        }

    base = CrawlerAccount.objects.filter(platform='11st')
    if focused_only:
        base = base.filter(is_focused=True)
    base = guard.exclude_perma_banned(base)   # 영구정지 계정 제외
    all_accounts = list(base.exclude(api_key=''))
    skipped_no_key = list(base.filter(api_key='').values_list('login_id', flat=True))

    # 1) 신선도 필터 — 최근 동기화된 계정 스킵
    skipped_recent = []
    if skip_recent and not force:
        recent_map = {
            x['account_id']: x['last_synced']
            for x in ElevenMyProduct.objects.values('account_id')
                .annotate(last_synced=Max('synced_at'))
        }
        accounts = []
        for a in all_accounts:
            if guard.is_recently_synced(recent_map.get(a.id), hours=RECENT_SYNC_HOURS):
                skipped_recent.append(a.login_id)
            else:
                accounts.append(a)
    else:
        accounts = all_accounts

    sess = _make_session()
    results = []
    total = len(accounts)
    consecutive_fail = 0
    aborted = False

    if log_fn:
        log_fn(f'대상 {total}계정 (신규/만료) — 최근 {RECENT_SYNC_HOURS}h 내 성공 {len(skipped_recent)}개 스킵')

    for i, acct in enumerate(accounts):
        # 매 계정 시작 전에도 글로벌 락 확인 (다른 작업이 차단 락 걸었을 수 있음)
        if guard.guard_and_skip(f'OpenAPI[{acct.login_id}]'):
            aborted = True
            if log_fn:
                log_fn('⛔ 진행 중 글로벌 차단 활성화 — 즉시 중단')
            break

        if log_fn:
            log_fn(f'[{i+1}/{total}] {acct.login_id} 동기화 시작')
        r = sync_products_for_account(acct.id, log_fn=log_fn, session=sess)
        results.append(r)

        # circuit breaker
        err = r.get('error', '') if isinstance(r, dict) else ''
        if err and guard.is_block_signal(err):
            consecutive_fail += 1
            if consecutive_fail >= fail_fast_threshold:
                # 글로벌 차단 락 발동 (이미 _fetch_products_page에서 했을 수도 있지만 보강)
                guard.report_signal(err, source='sync_focused_accounts')
                aborted = True
                if log_fn:
                    log_fn(f'⛔ 연속 차단신호 {consecutive_fail}회 — 글로벌 차단 락 발동, 중단')
                break
        else:
            consecutive_fail = 0

        if i < total - 1:
            wait = random.uniform(*ACCOUNT_SLEEP)
            if log_fn:
                log_fn(f'다음 계정까지 {wait:.1f}s 대기...')
            time.sleep(wait)

    guard.release_global_lock()   # 전역 락 해제 (동시 크롤 금지 유지)
    return {
        'accounts': results,
        'skipped_no_api_key': skipped_no_key,
        'skipped_recent': skipped_recent,
        'total_accounts': len(results),
        'aborted_due_to_block_signal': aborted,
    }


_SORT_MAP = {
    'product_no': 'product_no', 'product_name': 'product_name', 'sale_price': 'sale_price',
    'stock_quantity': 'stock_quantity', 'status_type': 'status_type',
    'seller_product_code': 'seller_product_code', 'category_id': 'category_id',
    'seller_name': 'account__seller_name', 'login_id': 'account__login_id', 'synced_at': 'synced_at',
}


def get_my_products(account_id=None, page=1, per_page=50, status=None, search=None,
                    focused_only=False, sort=None, order='asc', needs_check=False):
    from django.core.cache import cache
    qs = ElevenMyProduct.objects.select_related('account').all()
    if account_id:
        qs = qs.filter(account_id=account_id)
    if status:
        qs = qs.filter(status_type=status)
    if search:
        qs = qs.filter(product_name__icontains=search) | qs.filter(seller_product_code__icontains=search)
    if focused_only:
        # 조인(account__is_focused) 대신 account_id IN 으로 필터 → synced_at 인덱스로 정렬+LIMIT 가능
        # (조인 시 ~36만행을 temp+filesort 하느라 페이지당 수 분 걸리던 문제 해결)
        focused_ids = list(
            CrawlerAccount.objects.filter(platform='11st', is_focused=True).values_list('id', flat=True)
        )
        qs = qs.filter(account_id__in=focused_ids)

    # 확인필요 = 역마진(구매원가>판매가 → cost_diff<0). 현재 필터 기준 건수(배지표시용, 캐시).
    nc_key = f"emp_needs:{account_id}:{status}:{search}:{int(bool(focused_only))}"
    needs_total = cache.get(nc_key)
    if needs_total is None:
        needs_total = qs.filter(cost_diff__lt=0).count()
        cache.set(nc_key, needs_total, 120)

    if needs_check:
        # 확인필요만 보기 — 역마진 행만, 가장 심한(음수 큰) 순으로 맨 위에.
        qs = qs.filter(cost_diff__lt=0)

    from django.db.models import F
    if needs_check and not sort:
        qs = qs.order_by(F('cost_diff').asc(nulls_last=True), '-id')   # 기본: 역마진 심한 순(맨 위)
    elif sort in ('purchase_cost', 'cost_diff'):
        # 구매원가/차이는 비정규화 컬럼(인덱스)로 정렬 — 매칭없음(NULL)은 항상 맨 뒤.
        col = 'purchase_cost' if sort == 'purchase_cost' else 'cost_diff'
        nulls = F(col).asc(nulls_last=True) if order == 'asc' else F(col).desc(nulls_last=True)
        qs = qs.order_by(nulls, '-id')
    elif sort in _SORT_MAP:
        field = _SORT_MAP[sort]
        if order == 'desc':
            field = '-' + field
        qs = qs.order_by(field, '-id')
    else:
        qs = qs.order_by('-synced_at', '-id')
    # COUNT(*)는 45만행 인덱스 카운트라 4~10초로 페이지 이동마다 병목 → 필터별 캐시.
    # 데이터는 동기화(크롤) 때만 변하므로 120초 TTL이면 충분(총개수는 페이징 표시용).
    if needs_check:
        total = needs_total
    else:
        count_key = f"emp_count:{account_id}:{status}:{search}:{int(bool(focused_only))}"
        total = cache.get(count_key)
        if total is None:
            total = qs.count()
            cache.set(count_key, total, 120)
    offset = (page - 1) * per_page
    items = list(qs[offset:offset + per_page])
    serialized = [_serialize(p) for p in items]
    _attach_purchase_cost(serialized)

    return {
        'items': serialized,
        'total': total,
        'needs_check_total': needs_total,   # 확인필요(역마진) 건수 — 필터 on/off 무관 항상 제공
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page if total > 0 else 0,
    }


def _attach_purchase_cost(serialized):
    """마켓가(예비상품 ownerclan market_price=마켓실제판매가)를 11번가 판매자코드(seller_product_code=ownerclan product_code)로 매칭해 주입.
    - purchase_cost: ownerclan.market_price (마켓가). 사용자 요청대로 마켓가 기준.
    - cost_diff: 판매가 - 마켓가"""
    codes = [s['seller_product_code'] for s in serialized if s.get('seller_product_code')]
    cost_map = {}
    if codes:
        from apps.ownerclan.models import OwnerclanProduct
        for o in (OwnerclanProduct.objects.filter(product_code__in=codes)
                  .values('product_code', 'market_price')):
            cost_map.setdefault(o['product_code'], o['market_price'])
    for s in serialized:
        pc = cost_map.get(s.get('seller_product_code')) or None
        if not pc:   # 0 또는 미존재 → 데이터 없음
            s['purchase_cost'] = None
            s['cost_diff'] = None
            continue
        s['purchase_cost'] = pc
        sp = s.get('sale_price')
        s['cost_diff'] = (sp - pc) if sp is not None else None


def refresh_purchase_costs(codes=None):
    """eleven_my_product.purchase_cost 를 예비상품(ownerclan) 마켓가(market_price=마켓실제판매가)로 갱신(set-based JOIN).
    seller_product_code = ownerclan.product_code 매칭. market_price 0/미존재는 NULL.
    (사용자 요청: /myproduct 표시는 '마켓가' 기준). cost_diff(생성컬럼)=판매가-마켓가 자동 재계산.
    - codes=None: 전체 갱신 (상품 크롤 후)
    - codes=[...]: 해당 예비상품 코드와 매칭되는 행만 갱신 (예비상품 업로드 직후, 빠름)"""
    from django.db import connection
    code_list = None
    if codes is not None:
        code_list = [c for c in {str(x).strip() for x in codes} if c]
        if not code_list:
            return 0
    with connection.cursor() as c:
        if code_list is None:
            # 전체
            c.execute("""
                UPDATE eleven_my_product e
                JOIN ownerclan_product o ON o.product_code = e.seller_product_code
                SET e.purchase_cost = NULLIF(o.market_price, 0)
                WHERE e.seller_product_code <> ''
            """)
            updated = c.rowcount
            c.execute("""
                UPDATE eleven_my_product e
                LEFT JOIN ownerclan_product o ON o.product_code = e.seller_product_code
                SET e.purchase_cost = NULL
                WHERE e.purchase_cost IS NOT NULL
                  AND (e.seller_product_code = '' OR o.product_code IS NULL OR o.market_price = 0)
            """)
            return updated
        # incremental — 청크로 IN 처리 (seller_product_code 인덱스 사용)
        updated = 0
        for i in range(0, len(code_list), 5000):
            chunk = code_list[i:i + 5000]
            ph = ','.join(['%s'] * len(chunk))
            c.execute(f"""
                UPDATE eleven_my_product e
                LEFT JOIN ownerclan_product o ON o.product_code = e.seller_product_code
                SET e.purchase_cost = NULLIF(o.market_price, 0)
                WHERE e.seller_product_code IN ({ph})
            """, chunk)
            updated += c.rowcount
        return updated


def get_my_product_detail(product_pk):
    try:
        p = ElevenMyProduct.objects.select_related('account').get(pk=product_pk)
    except ElevenMyProduct.DoesNotExist:
        return None
    s = _serialize(p)
    _attach_purchase_cost([s])
    return s


def _serialize(p):
    return {
        'id': p.id,
        'account_id': p.account_id,
        'login_id': p.account.login_id,
        'seller_name': p.account.seller_name,
        'is_focused': p.account.is_focused,
        'product_no': p.product_no,
        'product_name': p.product_name,
        'sale_price': p.sale_price,
        'stock_quantity': p.stock_quantity,
        'status_type': p.status_type,
        'seller_product_code': p.seller_product_code,
        'category_id': p.category_id,
        'product_image_url': p.product_image_url,
        'synced_at': p.synced_at.isoformat() if p.synced_at else None,
        'created_at': p.created_at.isoformat() if p.created_at else None,
        'updated_at': p.updated_at.isoformat() if p.updated_at else None,
    }


def _office_payload(o):
    if not o:
        return {
            'office_collected_at': None,
            'office_cash': None, 'office_point': None, 'office_ad_balance': None,
            'product_limit': None, 'products': None, 'banned': None, 'available': None,
            'overdue': None, 'undelivered': None, 'draft': None,
            'fulfillment': '', 'shipping': '', 'inquiry': '',
            'office_error': '',
        }
    return {
        'office_collected_at': o.collected_at.isoformat() if o.collected_at else None,
        'office_cash': o.cash, 'office_point': o.point, 'office_ad_balance': o.ad_balance,
        'product_limit': o.product_limit, 'products': o.products,
        'banned': o.banned, 'available': o.available,
        'overdue': o.overdue, 'undelivered': o.undelivered, 'draft': o.draft,
        'fulfillment': o.fulfillment, 'shipping': o.shipping, 'inquiry': o.inquiry,
        'office_error': o.error or '',
    }


def get_account_summary(all_accounts=False):
    from django.db.models import Count, Max, Sum, Q
    from django.core.cache import cache
    from datetime import timedelta
    from .models import ElevenSellerGrade, ElevenCostHistory, ElevenSellerOfficeStat

    # 계정요약은 크롤(동기화) 때만 변함 → 120초 캐시. (balance/products 집계가 무거움)
    cache_key = 'eleven_acct_summary_all' if all_accounts else 'eleven_acct_summary'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    qs_acct = CrawlerAccount.objects.filter(platform='11st', is_active=True)
    if not all_accounts:
        qs_acct = qs_acct.filter(is_focused=True)
    accounts = list(qs_acct)
    login_ids = [a.login_id for a in accounts]
    account_ids = [a.id for a in accounts]

    office_map = {}
    office_qs = ElevenSellerOfficeStat.objects.filter(account_id__in=account_ids).order_by('account_id', '-collected_at')
    for o in office_qs:
        if o.account_id not in office_map:
            office_map[o.account_id] = o

    products_agg = {
        x['account_id']: x for x in
        ElevenMyProduct.objects.filter(account_id__in=account_ids)
            .values('account_id')
            .annotate(product_count=Count('id'), last_synced=Max('synced_at'))
    }

    # 등급: login_id별 가장 최근
    grade_map = {}
    grade_qs = ElevenSellerGrade.objects.filter(eleven_id__in=login_ids).order_by('eleven_id', '-collected_at')
    for g in grade_qs:
        if g.eleven_id not in grade_map:
            grade_map[g.eleven_id] = g

    # 잔액: seller_id별 가장 최근 거래의 balance
    # 기존엔 focused 셀러 거래 20.8만행을 전부 파이썬으로 끌어와(~4.4초) 셀러별 첫행만 남김 → N행 전량스캔.
    # id IN (셀러별 Max(id)) 배치로 변경(~0.3초). id는 삽입=거래시각순이라 최신 proxy.
    bal_ids = list(ElevenCostHistory.objects.filter(seller_id__in=login_ids)
                   .values('seller_id').annotate(mx=Max('id')).values_list('mx', flat=True))
    balance_map = {h.seller_id: h for h in ElevenCostHistory.objects.filter(id__in=bal_ids)}

    # 광고비 30일 합계 (amount<0인 것 abs sum) — seller_id별
    cutoff = timezone.now() - timedelta(days=30)
    cost30_qs = (
        ElevenCostHistory.objects
        .filter(seller_id__in=login_ids, transaction_datetime__gte=cutoff, amount__lt=0)
        .values('seller_id')
        .annotate(total=Sum('amount'))
    )
    cost30_map = {row['seller_id']: abs(row['total'] or 0) for row in cost30_qs}

    rows = []
    for a in accounts:
        agg = products_agg.get(a.id, {})
        g = grade_map.get(a.login_id)
        b = balance_map.get(a.login_id)
        rows.append({
            'account_id': a.id,
            'login_id': a.login_id,
            'seller_name': a.seller_name,
            'cost_type': a.cost_type,
            'crawling_status': a.crawling_status,
            'fail_count': a.fail_count,
            'last_crawled_at': a.last_crawled_at.isoformat() if a.last_crawled_at else None,
            'has_api_key': bool(a.api_key),
            'api_key_masked': ('****' + a.api_key[-4:]) if a.api_key else '',
            'product_count': agg.get('product_count', 0),
            'last_synced': agg['last_synced'].isoformat() if agg.get('last_synced') else None,
            'grade': g.grade if g else None,
            'grade_message': g.grade_message if g else '',
            'required_sales': g.required_sales if g else None,
            'grade_collected_at': g.collected_at.isoformat() if g and g.collected_at else None,
            'balance': b.balance if b else None,
            'balance_at': b.transaction_datetime.isoformat() if b and b.transaction_datetime else None,
            'cost_30days': cost30_map.get(a.login_id, 0),
            **(_office_payload(office_map.get(a.id))),
        })
    # 정렬: 1>2>3>4등급 → 최근30일 광고비 소진 계정 → 나머지, 각 그룹 내 아이디 알파벳순
    def _rank(r):
        g = r.get('grade')
        if g in (1, 2, 3, 4):
            tier = g
        elif (r.get('cost_30days') or 0) > 0:
            tier = 5
        else:
            tier = 6
        return (tier, str(r.get('login_id') or '').lower())
    rows.sort(key=_rank)
    result = {'accounts': rows}
    cache.set(cache_key, result, 120)
    return result


def trigger_integrated_sync(tasks=None, account_id=None):
    """통합 동기화 — 모두 백그라운드 서브프로세스로 실행 (워커 비차단).
    글로벌 차단 락 활성 시 subprocess 자체를 띄우지 않음."""
    import os, sys, subprocess
    from django.conf import settings as django_settings

    # 글로벌 차단 락 — subprocess 띄우지 말고 즉시 반환
    blocked, remaining, until = guard.is_blocked()
    if blocked:
        return {
            'started': [],
            'aborted_due_to_global_block': True,
            'block_remaining_seconds': remaining,
            'block_until': until.isoformat() if until else None,
            'message': f'⛔ 11번가 글로벌 차단 모드 — 작업 시작 안 함 ({remaining}초 후 해제)',
        }

    valid = {'products', 'grade', 'cost', 'office'}
    if not tasks:
        tasks = list(valid)
    else:
        tasks = [t for t in tasks if t in valid]

    started = []
    products_result = None

    manage_py = os.path.join(django_settings.BASE_DIR, 'manage.py')

    if 'products' in tasks:
        log_path = '/tmp/sync_eleven_my_products.log'
        cmd_args = [sys.executable, manage_py, 'sync_eleven_my_products']
        if account_id:
            cmd_args += ['--account-id', str(account_id)]
        else:
            cmd_args.append('--all')
        try:
            with open(log_path, 'a') as logf:
                subprocess.Popen(
                    cmd_args,
                    stdout=logf, stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            started.append('products')
        except Exception as e:
            logger.exception('products subprocess launch failed')

    # 셀레늄 작업(grade/cost/office)은 chrome 동시 실행 race condition 방지를 위해
    # 단일 체인 subprocess가 순차 실행한다 (run_11st_selenium_chain).
    selenium_tasks = [t for t in ('grade', 'cost', 'office') if t in tasks]
    if selenium_tasks:
        log_path = '/tmp/cron_11st_selenium_chain.log'
        cmd_args = [
            sys.executable, manage_py, 'run_11st_selenium_chain',
            '--tasks', ','.join(selenium_tasks),
        ]
        if account_id:
            cmd_args += ['--account-id', str(account_id)]
        try:
            with open(log_path, 'a') as logf:
                subprocess.Popen(
                    cmd_args,
                    stdout=logf, stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            for t in selenium_tasks:
                started.append(t)
        except Exception as e:
            logger.exception('selenium chain subprocess launch failed')

    return {
        'started': started,
        'message': '통합 동기화 시작됨 (백그라운드 실행)',
    }


def _normalize_name(name):
    """상품명 정규화: 특수문자 제거, 공백 압축, 소문자"""
    import re
    if not name:
        return ''
    s = re.sub(r'[^\w가-힣]+', '', name).lower()
    return s


def find_duplicates(mode='strict'):
    """중복 등록 위험 상품 그룹화.
    mode: 'strict' = 상품명+가격 정확 일치
          'loose'  = 정규화 상품명 일치 (특수문자/공백 무시)
          'image'  = 이미지 URL 일치
    """
    from django.db.models import Count
    qs = ElevenMyProduct.objects.select_related('account').all()
    items = list(qs)
    groups = {}

    for p in items:
        if mode == 'strict':
            key = ('name+price', (p.product_name or '').strip(), p.sale_price)
            if not key[1]:
                continue
        elif mode == 'loose':
            norm = _normalize_name(p.product_name)
            if not norm:
                continue
            key = ('norm_name', norm)
        elif mode == 'image':
            url = (p.product_image_url or '').strip()
            if not url:
                continue
            key = ('image', url)
        else:
            continue

        groups.setdefault(key, []).append(p)

    result = []
    for key, plist in groups.items():
        if len(plist) < 2:
            continue
        result.append({
            'group_key': '|'.join(str(x) for x in key),
            'kind': key[0],
            'count': len(plist),
            'sample_name': plist[0].product_name,
            'sample_price': plist[0].sale_price,
            'sample_image': plist[0].product_image_url,
            'items': [
                {
                    'id': p.id,
                    'account_id': p.account_id,
                    'login_id': p.account.login_id,
                    'seller_name': p.account.seller_name,
                    'product_no': p.product_no,
                    'product_name': p.product_name,
                    'sale_price': p.sale_price,
                    'stock_quantity': p.stock_quantity,
                    'status_type': p.status_type,
                    'product_image_url': p.product_image_url,
                    'seller_product_code': p.seller_product_code,
                    'category_id': p.category_id,
                }
                for p in plist
            ],
        })

    result.sort(key=lambda g: g['count'], reverse=True)
    total_dup_items = sum(g['count'] for g in result)
    return {
        'mode': mode,
        'group_count': len(result),
        'total_duplicate_items': total_dup_items,
        'total_scanned': len(items),
        'groups': result,
    }


def _is_pid_alive(pid):
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError):
        return False


def _tail_lines(path, n=30):
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'rb') as f:
            try:
                f.seek(-65536, os.SEEK_END)
            except OSError:
                f.seek(0)
            data = f.read().decode('utf-8', errors='replace')
        lines = [ln for ln in data.split('\n') if ln.strip()]
        return lines[-n:]
    except Exception:
        return []


def _scan_running_processes():
    """ps로 11번가 관련 manage.py 프로세스 검색"""
    import subprocess
    try:
        out = subprocess.check_output(
            ['ps', '-eo', 'pid,etime,args'], text=True, errors='replace',
        )
    except Exception:
        return {}
    procs = {'cost': [], 'grade': [], 'products': [], 'office': []}
    for line in out.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        pid, etime, cmd = parts
        if 'manage.py' not in cmd:
            continue
        if 'crawl_11st_office' in cmd:
            procs['office'].append({'pid': int(pid), 'etime': etime})
        elif 'crawl_11st_cost' in cmd:
            procs['cost'].append({'pid': int(pid), 'etime': etime})
        elif 'crawl_11st_grade' in cmd:
            procs['grade'].append({'pid': int(pid), 'etime': etime})
        elif 'sync_eleven_my_products' in cmd:
            procs['products'].append({'pid': int(pid), 'etime': etime})
    return procs


def get_sync_status():
    """11번가 크롤러 진행상황 통합 조회"""
    from .models import (
        ElevenSellerGrade, ElevenCostHistory, ElevenMyProduct, CrawlerAccount,
        ElevenSellerOfficeStat,
    )
    from django.db.models import Max, Count

    procs = _scan_running_processes()

    cost_log = _tail_lines('/tmp/cron_11st_cost.log', 30)
    grade_log = _tail_lines('/tmp/cron_grade.log', 30)
    office_log = _tail_lines('/tmp/cron_11st_office.log', 30)

    def _current_account_from_log(lines):
        import re
        for ln in reversed(lines):
            m = re.search(r'\[11st:([^\]]+)\]', ln)
            if m:
                return m.group(1)
        return None

    cost_max = ElevenCostHistory.objects.aggregate(m=Max('created_at'))['m']
    grade_max = ElevenSellerGrade.objects.aggregate(m=Max('collected_at'))['m']
    products_max = ElevenMyProduct.objects.aggregate(m=Max('synced_at'))['m']
    products_count = ElevenMyProduct.objects.count()
    accounts_with_products = ElevenMyProduct.objects.values('account_id').distinct().count()

    focused_total = CrawlerAccount.objects.filter(
        platform='11st', is_focused=True,
    ).count()
    focused_with_key = CrawlerAccount.objects.filter(
        platform='11st', is_focused=True,
    ).exclude(api_key='').count()

    return {
        'focused_accounts': focused_total,
        'focused_with_api_key': focused_with_key,
        'cost': {
            'running': len(procs['cost']) > 0,
            'pids': procs['cost'],
            'last_db_at': cost_max.isoformat() if cost_max else None,
            'current_account': _current_account_from_log(cost_log) if procs['cost'] else None,
            'tail_log': cost_log,
        },
        'grade': {
            'running': len(procs['grade']) > 0,
            'pids': procs['grade'],
            'last_db_at': grade_max.isoformat() if grade_max else None,
            'current_account': _current_account_from_log(grade_log) if procs['grade'] else None,
            'tail_log': grade_log,
        },
        'products': {
            'running': len(procs['products']) > 0,
            'pids': procs['products'],
            'last_db_at': products_max.isoformat() if products_max else None,
            'total_products': products_count,
            'accounts_with_products': accounts_with_products,
        },
        'office': {
            'running': len(procs['office']) > 0,
            'pids': procs['office'],
            'last_db_at': (lambda m: m.isoformat() if m else None)(
                ElevenSellerOfficeStat.objects.aggregate(m=Max('collected_at'))['m']
            ),
            'tail_log': office_log,
        },
    }
