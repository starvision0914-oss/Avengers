"""
네이버 커머스 API 상품 동기화 (ai100 참조)
OAuth2 + bcrypt 서명 방식
"""
import time
import base64
import logging
from datetime import datetime, date, timedelta
from collections import defaultdict

import bcrypt
import requests

logger = logging.getLogger('smartstore')

NAVER_TOKEN_URL = 'https://api.commerce.naver.com/external/v1/oauth2/token'
NAVER_PRODUCTS_URL = 'https://api.commerce.naver.com/external/v1/products/search'
NAVER_PRODUCT_URL = 'https://api.commerce.naver.com/external/v2/products/origin-products/{origin_product_no}'
NAVER_CHANNEL_PRODUCT_URL = 'https://api.commerce.naver.com/external/v2/products/channel-products/{channel_product_no}'
NAVER_ORDER_STATUS_URL = 'https://api.commerce.naver.com/external/v1/pay-order/seller/product-orders/last-changed-statuses'


def _get_access_token(client_id: str, client_secret: str) -> str:
    timestamp = int(time.time() * 1000)
    password = f'{client_id}_{timestamp}'
    hashed = bcrypt.hashpw(password.encode(), client_secret.encode())
    signature = base64.b64encode(hashed).decode()

    resp = requests.post(NAVER_TOKEN_URL, data={
        'client_id': client_id,
        'timestamp': timestamp,
        'client_secret_sign': signature,
        'grant_type': 'client_credentials',
        'type': 'SELF',
    }, timeout=15)
    resp.raise_for_status()
    return resp.json()['access_token']


def _fetch_products_page(token: str, page: int = 1, size: int = 100) -> dict:
    headers = {'Authorization': f'Bearer {token}'}
    for attempt in range(4):
        resp = requests.post(NAVER_PRODUCTS_URL, json={'page': page, 'size': size},
                             headers=headers, timeout=30)
        if resp.status_code == 429:
            wait = 30 * (attempt + 1)
            logger.warning('429 rate limit page=%s attempt=%s, waiting %ss', page, attempt, wait)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()
    return {}


def fetch_all_products(client_id: str, client_secret: str) -> list:
    token = _get_access_token(client_id, client_secret)
    products = []
    page = 1
    while True:
        data = _fetch_products_page(token, page)
        contents = data.get('contents', [])
        if not contents:
            break
        products.extend(contents)
        if page >= data.get('totalPages', 1):
            break
        page += 1
        time.sleep(0.5)
    return products


def sync_products_api(account) -> dict:
    """네이버 커머스 API로 상품 동기화. account: SmartStoreAccount 인스턴스"""
    from apps.smartstore.models import SmartStoreProduct

    if not account.commerce_api_key or not account.commerce_secret_key:
        return {'error': 'API 키 미등록'}

    try:
        products = fetch_all_products(account.commerce_api_key, account.commerce_secret_key)
    except Exception as e:
        logger.exception('Naver API error account=%s', account.id)
        return {'error': f'네이버 API 오류: {e}'}

    upserted = 0
    now = datetime.now()

    for p in products:
        origin_no = str(p.get('originProductNo', ''))
        if not origin_no:
            continue

        cp = {}
        channel_list = p.get('channelProducts', [])
        if channel_list:
            cp = channel_list[0]

        image_url = ''
        ri = cp.get('representativeImage')
        if isinstance(ri, dict):
            image_url = ri.get('url', '')

        SmartStoreProduct.objects.update_or_create(
            account=account,
            product_no=origin_no,
            defaults=dict(
                channel_product_no=str(cp.get('channelProductNo', '') or ''),
                name=((cp.get('name') or p.get('name') or '') or '')[:500],
                sale_price=int(cp.get('salePrice', 0) or 0),
                stock_quantity=int(cp.get('stockQuantity', 0) or 0),
                status_type=cp.get('statusType', '') or '',
                seller_management_code=(cp.get('sellerManagementCode', '') or '')[:200],
                category_id=str(cp.get('wholeCategoryId', '') or ''),
                product_image_url=image_url,
                synced_at=now,
            ),
        )
        upserted += 1

    return {
        'synced': upserted,
        'total_from_api': len(products),
        'store_name': account.display_name or account.store_name,
        'synced_at': now.isoformat(),
    }


def _fetch_orders_for_day(token: str, day: date) -> list:
    """하루치 주문 상태 변경 내역 수집 (최대 24h 범위 제한)."""
    headers = {'Authorization': f'Bearer {token}'}
    from_dt = datetime(day.year, day.month, day.day, 0, 0, 0).strftime('%Y-%m-%dT%H:%M:%S.0Z')
    to_dt = datetime(day.year, day.month, day.day, 23, 59, 59).strftime('%Y-%m-%dT%H:%M:%S.0Z')
    items = []
    last_seq = None
    while True:
        params = {
            'lastChangedFrom': from_dt,
            'lastChangedTo': to_dt,
            'limitCount': 300,
        }
        if last_seq is not None:
            params['moreSequence'] = last_seq
        try:
            resp = requests.get(NAVER_ORDER_STATUS_URL, params=params, headers=headers, timeout=10)
        except Exception:
            break
        if resp.status_code in (429, 500, 502, 503):
            time.sleep(2)
            break
        if resp.status_code != 200:
            break
        data = resp.json()
        batch = data.get('productOrderInfoList', [])
        items.extend(batch)
        if not data.get('hasMore'):
            break
        last_seq = data.get('nextSequence')
        if last_seq is None:
            break
        time.sleep(0.3)
    return items


def sync_sales_api(account, start_date: date, end_date: date) -> dict:
    """Commerce API 주문 상태 변경 내역으로 일별 집계 → SmartStoreSales 저장."""
    from apps.smartstore.models import SmartStoreSales

    if not account.commerce_api_key or not account.commerce_secret_key:
        return {'error': 'API 키 미등록', 'saved': 0}

    try:
        token = _get_access_token(account.commerce_api_key, account.commerce_secret_key)
    except Exception as e:
        return {'error': f'토큰 오류: {e}', 'saved': 0}

    daily: dict = defaultdict(lambda: {
        'order_count': 0, 'sales_amount': 0, 'cancel_amount': 0,
        'return_amount': 0, 'settlement_amount': 0, 'commission_amount': 0,
    })

    cur = start_date
    while cur <= end_date:
        items = _fetch_orders_for_day(token, cur)
        for item in items:
            order = item.get('productOrder', item)
            status = order.get('productOrderStatus', '')
            pay_amt = int(order.get('totalPaymentAmount', 0) or 0)
            settle_amt = int(order.get('settlementAmount', order.get('expectedSettlementAmount', 0)) or 0)
            commission = int(order.get('commissionAmount', 0) or 0)

            if status in ('PURCHASE_DECIDED', 'DELIVERED', 'PAYMENT_WAITING', 'PAYED', 'DELIVERING'):
                row = daily[cur]
                row['order_count'] += 1
                row['sales_amount'] += pay_amt
                row['settlement_amount'] += settle_amt
                row['commission_amount'] += commission
            elif status in ('CANCELED', 'CANCEL_DONE'):
                daily[cur]['cancel_amount'] += pay_amt
            elif status in ('RETURNED', 'RETURN_DONE'):
                daily[cur]['return_amount'] += pay_amt

        cur += timedelta(days=1)
        time.sleep(0.3)

    saved = 0
    for d, row in daily.items():
        if any(v for v in row.values()):
            SmartStoreSales.objects.update_or_create(
                account=account, date=d,
                defaults=row,
            )
            saved += 1

    return {'saved': saved, 'store_name': account.display_name}


def suspend_product_api(channel_product_no: str, token: str):
    """상품을 SUSPENSION 상태로 변경.
    channel-products 엔드포인트 사용 필수(2026-08-22) — origin-products로 originProduct만 PUT하면
    필수 동반 필드(smartstoreChannelProduct) 누락 + seoInfo 금지단어/unitCapacity.unitPriceYn 누락으로
    400 Bad Request 대량 발생(apply_ss_products.py에서 검증된 정상 패턴을 이식)."""
    url = NAVER_CHANNEL_PRODUCT_URL.format(channel_product_no=channel_product_no)
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    get_resp = requests.get(url, headers=headers, timeout=30)
    get_resp.raise_for_status()
    data = get_resp.json()
    op = data.get('originProduct', {})
    op['statusType'] = 'SUSPENSION'

    # seoInfo에 금지단어가 있으면 PUT 400 → 제거
    op.get('detailAttribute', {}).pop('seoInfo', None)
    # unitCapacity.unitPriceYn 누락/null이면 PUT 400 → false로 보정
    da = op.setdefault('detailAttribute', {})
    unit_cap = da.get('unitCapacity')
    if unit_cap is None:
        da['unitCapacity'] = {'unitPriceYn': False}
    elif 'unitPriceYn' not in unit_cap:
        unit_cap['unitPriceYn'] = False
    # 카테고리가 인증대상이 아닌데 productCertificationInfos가 남아있으면 PUT 400
    # (2026-08-24, 스타주노 뽀로로 직소퍼즐: NotAllowCategory.../certificationInfos.kindType) → 제거
    # (2026-08-24) 인증대상 아닌 카테고리에서 남은 productCertificationInfos가 400을 유발해 무조건
    # 제거했었는데, KC인증 "대상" 카테고리에서는 반대로 이게 없으면 "인증 종류를 선택하셔야 합니다"
    # 400이 남(2026-08-26 실측, 유진코리아몰 다수 상품). kindType이 비어있는 불완전한 항목만 제거하고
    # 정상적으로 채워진 인증정보는 그대로 둔다.
    certs = da.get('productCertificationInfos')
    if isinstance(certs, list):
        da['productCertificationInfos'] = [c for c in certs if c.get('certificationKindType')]
        if not da['productCertificationInfos']:
            da.pop('productCertificationInfos', None)

    put_resp = requests.put(
        url,
        json={'originProduct': op, 'smartstoreChannelProduct': data.get('smartstoreChannelProduct', {})},
        headers=headers, timeout=30,
    )
    put_resp.raise_for_status()
    return put_resp.json()


def _apply_common_fixups(op):
    """suspend_product_api/update_price_api와 동일한 PUT 400 방지 보정(seoInfo/unitCapacity/인증정보)."""
    da = op.setdefault('detailAttribute', {})
    da.pop('seoInfo', None)
    unit_cap = da.get('unitCapacity')
    if unit_cap is None:
        da['unitCapacity'] = {'unitPriceYn': False}
    elif 'unitPriceYn' not in unit_cap:
        unit_cap['unitPriceYn'] = False
    certs = da.get('productCertificationInfos')
    if isinstance(certs, list):
        da['productCertificationInfos'] = [c for c in certs if c.get('certificationKindType')]
        if not da['productCertificationInfos']:
            da.pop('productCertificationInfos', None)


def sync_stock_from_ownerclan(channel_product_no: str, token: str, ownerclan_item: dict):
    """오너클랜 실재고(옵션별 status/quantity)를 스마트스토어 옵션(sellerManagerCode로 매칭)에 반영.
    반환: {'changed': bool, 'new_status': str, 'detail': [...]}"""
    url = NAVER_CHANNEL_PRODUCT_URL.format(channel_product_no=channel_product_no)
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    get_resp = requests.get(url, headers=headers, timeout=30)
    get_resp.raise_for_status()
    data = get_resp.json()
    op = data.get('originProduct', {})
    da = op.setdefault('detailAttribute', {})
    old_status = op.get('statusType')

    oc_options = {str(o['key']): o for o in (ownerclan_item.get('options') or [])}
    detail = []
    any_available = False

    option_info = da.get('optionInfo') or {}
    combos = option_info.get('optionCombinations') or []

    if combos:
        # 네이버 규칙: "옵션가 0원 + 사용가능"인 옵션이 최소 1개 있어야 PUT이 통과된다(기준옵션).
        # 그 기준옵션을 재고이유로 꺼버리면 전체 PUT이 400 나므로, 0원 옵션은 품절이어도 끄지 않는다.
        zero_price_codes = {str(c.get('sellerManagerCode') or '') for c in combos if not c.get('price')}

        for c in combos:
            code = str(c.get('sellerManagerCode') or '')
            oc_opt = oc_options.get(code)
            if oc_opt and oc_opt.get('status') == 'available' and (oc_opt.get('quantity') or 0) > 0:
                new_qty = int(oc_opt['quantity'])
                if c.get('stockQuantity') != new_qty or not c.get('usable'):
                    detail.append(f'옵션{code}: {c.get("stockQuantity")}→{new_qty}, usable={c.get("usable")}→True')
                c['stockQuantity'] = new_qty
                c['usable'] = True
                any_available = True
            elif code in zero_price_codes:
                # 기준옵션(0원)은 오너클랜에서 품절이어도 usable은 유지(네이버 필수조건), 재고만 0으로.
                if c.get('stockQuantity') != 0:
                    detail.append(f'옵션{code}(기준옵션): {c.get("stockQuantity")}→0, usable 유지')
                c['stockQuantity'] = 0
            else:
                if c.get('usable') and (c.get('stockQuantity') or 0) != 0:
                    detail.append(f'옵션{code}: {c.get("stockQuantity")}→0(오너클랜 품절/미매칭)')
                c['stockQuantity'] = 0
                c['usable'] = False
    else:
        # 옵션 없는 단일상품 — 상품 전체 재고로 판단
        item_available = ownerclan_item.get('status') == 'available'
        if item_available:
            any_available = True
            op['stockQuantity'] = max(op.get('stockQuantity') or 0, 1)

    new_status = 'SALE' if any_available else 'OUTOFSTOCK'
    changed = new_status != old_status or bool(detail)
    op['statusType'] = new_status

    if not changed:
        return {'changed': False, 'new_status': old_status, 'detail': []}

    _apply_common_fixups(op)
    put_resp = requests.put(
        url,
        json={'originProduct': op, 'smartstoreChannelProduct': data.get('smartstoreChannelProduct', {})},
        headers=headers, timeout=30,
    )
    put_resp.raise_for_status()
    return {'changed': True, 'new_status': new_status, 'detail': detail}


def update_price_api(channel_product_no: str, new_price: int, token: str):
    """상품 판매가(salePrice)를 변경. suspend_product_api와 동일 GET→보정→PUT 패턴 재사용."""
    url = NAVER_CHANNEL_PRODUCT_URL.format(channel_product_no=channel_product_no)
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    get_resp = requests.get(url, headers=headers, timeout=30)
    get_resp.raise_for_status()
    data = get_resp.json()
    op = data.get('originProduct', {})
    op['salePrice'] = int(new_price)

    op.get('detailAttribute', {}).pop('seoInfo', None)
    da = op.setdefault('detailAttribute', {})
    unit_cap = da.get('unitCapacity')
    if unit_cap is None:
        da['unitCapacity'] = {'unitPriceYn': False}
    elif 'unitPriceYn' not in unit_cap:
        unit_cap['unitPriceYn'] = False
    # (2026-08-24) 인증대상 아닌 카테고리에서 남은 productCertificationInfos가 400을 유발해 무조건
    # 제거했었는데, KC인증 "대상" 카테고리에서는 반대로 이게 없으면 "인증 종류를 선택하셔야 합니다"
    # 400이 남(2026-08-26 실측, 유진코리아몰 다수 상품). kindType이 비어있는 불완전한 항목만 제거하고
    # 정상적으로 채워진 인증정보는 그대로 둔다.
    certs = da.get('productCertificationInfos')
    if isinstance(certs, list):
        da['productCertificationInfos'] = [c for c in certs if c.get('certificationKindType')]
        if not da['productCertificationInfos']:
            da.pop('productCertificationInfos', None)

    put_resp = requests.put(
        url,
        json={'originProduct': op, 'smartstoreChannelProduct': data.get('smartstoreChannelProduct', {})},
        headers=headers, timeout=30,
    )
    put_resp.raise_for_status()
    return put_resp.json()
