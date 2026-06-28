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


def suspend_product_api(origin_product_no: str, token: str):
    """상품을 SUSPENSION 상태로 변경"""
    url = NAVER_PRODUCT_URL.format(origin_product_no=origin_product_no)
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    get_resp = requests.get(url, headers=headers, timeout=30)
    get_resp.raise_for_status()
    product = get_resp.json()['originProduct']
    product['statusType'] = 'SUSPENSION'

    put_resp = requests.put(url, json={'originProduct': product}, headers=headers, timeout=30)
    put_resp.raise_for_status()
    return put_resp.json()
