"""쿠팡 오픈API(Wing Open API) 클라이언트.

HMAC 서명은 '?' 없이 datetime+method+path+query 순서로 조합해야 함
(2026-07-03 실측 확인 — 문서와 달리 '?' 포함시 서명오류(401) 발생).
IP 화이트리스트는 Wing > 오픈API 관리에서 등록 필요.
"""
import hashlib
import hmac
import time

import requests

BASE_URL = 'https://api-gateway.coupang.com'


def _signed_headers(account, method, path, query=''):
    datetime_str = time.strftime('%y%m%dT%H%M%SZ', time.gmtime())
    message = datetime_str + method + path + query
    signature = hmac.new(account.secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
    auth = (f'CEA algorithm=HmacSHA256, access-key={account.access_key}, '
            f'signed-date={datetime_str}, signature={signature}')
    return {
        'Authorization': auth,
        'Content-Type': 'application/json;charset=UTF-8',
        'X-EXTENDED-TIMEOUT': '90000',
    }


def _request(account, method, path, query=''):
    headers = _signed_headers(account, method, path, query)
    url = BASE_URL + path + (('?' + query) if query else '')
    r = requests.request(method, url, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()


def fetch_order_sheets(account, start_date, end_date, status='ACCEPT', max_per_page=50):
    """주문 목록 조회. start_date/end_date: date 객체, status: ACCEPT/INSTRUCT/DEPARTURE/DELIVERING/FINAL_DELIVERY.

    최대 조회 기간은 상태에 따라 제한(보통 최대 31일)이 있으므로 호출 측에서 분할할 것.
    """
    path = f'/v2/providers/openapi/apis/api/v4/vendors/{account.vendor_id}/ordersheets'
    query = (f'createdAtFrom={start_date.isoformat()}&createdAtTo={end_date.isoformat()}'
             f'&status={status}&maxPerPage={max_per_page}')
    return _request(account, 'GET', path, query)


ALL_STATUSES = ('ACCEPT', 'INSTRUCT', 'DEPARTURE', 'DELIVERING', 'FINAL_DELIVERY')


def fetch_all_order_sheets(account, start_date, end_date, log_fn=print):
    """모든 상태를 순회하며 주문 조회 (한 상태로는 특정 시점의 주문만 잡힘).

    상태 5개 연속 호출시 429(Too Many Requests) 실측됨 — 호출 간 짧은 대기 추가.
    """
    all_orders = []
    for status in ALL_STATUSES:
        time.sleep(0.3)
        try:
            resp = fetch_order_sheets(account, start_date, end_date, status=status)
            data = resp.get('data') or []
            log_fn(f'[쿠팡API:{account.login_id}] {status}: {len(data)}건')
            all_orders.extend(data)
        except requests.HTTPError as e:
            log_fn(f'[쿠팡API:{account.login_id}] {status} 조회 오류: {e} / {e.response.text[:300]}')
    return all_orders


def fetch_products(account, log_fn=print, max_per_page=50):
    """등록상품 전체 조회 (nextToken 페이징)."""
    path = '/v2/providers/seller_api/apis/api/v1/marketplace/seller-products'
    all_items = []
    next_token = ''
    page = 0
    while True:
        page += 1
        query = f'vendorId={account.vendor_id}&maxPerPage={max_per_page}'
        if next_token:
            query += f'&nextToken={next_token}'
        resp = _request(account, 'GET', path, query)
        data = resp.get('data') or []
        all_items.extend(data)
        log_fn(f'[쿠팡API:{account.login_id}] 상품 {page}페이지: {len(data)}건 (누적 {len(all_items)})')
        next_token = resp.get('nextToken') or ''
        if not next_token or not data:
            break
        time.sleep(0.3)
    return all_items


def save_products(account, products):
    from apps.coupang.models import CoupangProduct
    from django.utils.dateparse import parse_datetime
    from django.utils import timezone as dj_timezone

    def _aware(s):
        dt = parse_datetime(s or '')
        if dt and dj_timezone.is_naive(dt):
            dt = dj_timezone.make_aware(dt, dj_timezone.get_default_timezone())
        return dt

    saved = 0
    for p in products:
        seller_product_id = str(p.get('sellerProductId', ''))
        if not seller_product_id:
            continue
        CoupangProduct.objects.update_or_create(
            account=account, seller_product_id=seller_product_id,
            defaults={
                'product_name': p.get('sellerProductName', ''),
                'product_id': str(p.get('productId') or ''),
                'category_id': str(p.get('categoryId') or ''),
                'brand': p.get('brand', ''),
                'status_name': p.get('statusName', ''),
                'sale_started_at': _aware(p.get('saleStartedAt')),
                'sale_ended_at': _aware(p.get('saleEndedAt')),
                'registered_at': _aware(p.get('createdAt')),
            },
        )
        saved += 1
    return saved


def save_orders(account, order_sheets):
    """ordersheets 응답(data 리스트)을 CoupangOrder로 저장.

    orderedAt은 타임존 정보 없는 KST 문자열로 오므로 make_aware로 KST 부여
    (naive datetime을 그냥 저장하면 안 됨 — 타임존 함정).
    """
    from apps.coupang.models import CoupangOrder
    from django.utils.dateparse import parse_datetime
    from django.utils import timezone as dj_timezone

    saved = 0
    for sheet in order_sheets:
        order_id = str(sheet.get('orderId', ''))
        ordered_at = parse_datetime(sheet.get('orderedAt', '')) or None
        if ordered_at and dj_timezone.is_naive(ordered_at):
            ordered_at = dj_timezone.make_aware(ordered_at, dj_timezone.get_default_timezone())
        if not order_id or not ordered_at:
            continue
        for item in sheet.get('orderItems', []):
            vendor_item_id = str(item.get('vendorItemId', ''))
            CoupangOrder.objects.update_or_create(
                account=account, order_id=order_id, vendor_item_id=vendor_item_id,
                defaults={
                    'shipment_box_id': str(sheet.get('shipmentBoxId', '')),
                    'ordered_at': ordered_at,
                    'product_name': item.get('vendorItemName', '') or item.get('sellerProductName', ''),
                    'seller_product_id': str(item.get('sellerProductId', '')),
                    'quantity': item.get('shippingCount', 1),
                    'sales_price': item.get('orderPrice', 0),
                    'status': sheet.get('status', ''),
                },
            )
            saved += 1
    return saved
