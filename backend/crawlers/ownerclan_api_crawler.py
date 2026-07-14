"""오너클랜 정식 GraphQL API로 신규 상품을 자동 수집해 예비상품(ownerclan_product)에 추가.

인증: ownerclan.com 로그인과 동일한 판매사 ID/PW로 JWT 발급(30일 유효, 캐시해서 재사용).
  POST https://auth.ownerclan.com/auth {"service":"ownerclan","userType":"seller","username","password"}
조회: GET https://api.ownerclan.com/v1/graphql?query=... (Authorization: Bearer <토큰>)
  allItems(first, after, sortBy: dateDesc) — 최대 1000개/페이지, cursor 페이지네이션.

이미 DB에 있는 product_code(W코드)는 건너뛰고, 새로 발견된 상품만 INSERT한다
(services.ingest_playauto의 INSERT 패턴과 동일한 컬럼셋을 사용해 기존 예비상품과 스키마 일관성 유지).

실측 검증(2026-07-11, dlwodbs999): 인증 성공 + allItems 실제 상품데이터 조회 성공.
"""
import logging
from datetime import datetime, timedelta

import requests
from django.db import connections
from django.utils import timezone

logger = logging.getLogger('crawler')

AUTH_URL = 'https://auth.ownerclan.com/auth'
API_URL = 'https://api.ownerclan.com/v1/graphql'

STATUS_MAP = {'available': 1, 'soldout': 2, 'unavailable': 2, 'discontinued': 3}

PAGE_SIZE = 200  # 매뉴얼상 최대 1000이지만 실측 first:1000은 90초+ 응답없음(타임아웃) — 200은 2.4초로 안전


def _item_query(after=None):
    # GraphQL 쿼리변수($variables) 파라미터는 GET에서 400/타임아웃 발생(실측) — cursor를 리터럴로 인라인.
    after_clause = f', after: "{after}"' if after else ''
    return f"""
    query {{
      allItems(first: {PAGE_SIZE}{after_clause}, sortBy: dateDesc) {{
        pageInfo {{ hasNextPage endCursor }}
        edges {{
          node {{
            key
            name
            price
            fixedPrice
            shippingFee
            shippingType
            status
            production
            origin
            category {{ key fullName }}
            images(size: large)
          }}
        }}
      }}
    }}
    """


def _log(log_fn, m):
    logger.info(m)
    if log_fn:
        log_fn(m)


def _get_token(account, log_fn=None):
    now = timezone.now()
    if account.token and account.token_expires_at and account.token_expires_at > now + timedelta(hours=1):
        return account.token

    r = requests.post(AUTH_URL, json={
        'service': 'ownerclan', 'userType': 'seller',
        'username': account.login_id, 'password': account.login_pw,
    }, timeout=15)
    if r.status_code != 200 or not r.text.strip():
        _log(log_fn, f'[ownerclan-api:{account.login_id}] 인증 실패 HTTP {r.status_code}')
        return None

    token = r.text.strip()
    account.token = token
    account.token_expires_at = now + timedelta(days=29)  # 실제 만료 30일, 여유 1일
    account.save(update_fields=['token', 'token_expires_at'])
    _log(log_fn, f'[ownerclan-api:{account.login_id}] 토큰 발급 완료')
    return token


def _fetch_page(token, after=None):
    r = requests.get(API_URL, headers={'Authorization': f'Bearer {token}'},
                      params={'query': _item_query(after)},
                      timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get('errors'):
        raise RuntimeError(f'GraphQL 오류: {data["errors"]}')
    return data['data']['allItems']


def _existing_codes():
    with connections['default'].cursor() as cur:
        cur.execute("SELECT product_code FROM ownerclan_product")
        return {row[0] for row in cur.fetchall()}


def _empty_row(fields, int_fields, datetime_fields):
    """예비상품 스키마의 모든 트래킹 필드를 기본값(빈 문자열/0/NULL)으로 채운 dict.
    raw SQL INSERT라 컬럼 누락 시 'doesn't have a default value' 에러가 나므로 전체 컬럼을 항상 채운다."""
    return {f: (None if f in datetime_fields else (0 if f in int_fields else '')) for f in fields}


def crawl_new_items(account, log_fn=None, max_pages=None):
    """신규 상품(product_code가 아직 예비상품에 없는 것)만 골라 INSERT. 반환: {'new': n, 'scanned': n}."""
    from apps.ownerclan.services import EXCEL_COL_MAP, INT_FIELDS, DATETIME_FIELDS

    fields = list(EXCEL_COL_MAP.values())
    orig_fields = [f'orig_{f}' for f in fields]

    token = _get_token(account, log_fn)
    if not token:
        return {'error': '인증 실패', 'new': 0, 'scanned': 0}

    existing = _existing_codes()
    _log(log_fn, f'[ownerclan-api:{account.login_id}] 기존 예비상품 {len(existing):,}건 대비 신규 탐색 시작')

    now = datetime.now()
    new_rows = []  # [(product_code, data_dict), ...]
    scanned = 0
    after = None
    page = 0
    empty_streak = 0  # 연속으로 신규 0건인 페이지 수 (dateDesc 정렬이라 이 구간 이후는 이미 다 아는 상품)
    while True:
        page += 1
        result = _fetch_page(token, after)
        edges = result.get('edges', [])
        new_in_page = 0
        for edge in edges:
            n = edge['node']
            scanned += 1
            code = n['key']
            if code in existing:
                continue
            existing.add(code)
            new_in_page += 1
            images = n.get('images') or []
            cat = n.get('category') or {}
            data = _empty_row(fields, INT_FIELDS, DATETIME_FIELDS)
            data.update({
                'category_code': cat.get('key') or '',
                'category_name': cat.get('fullName') or '',
                'product_name': n.get('name') or '',
                'ownerclan_price': n.get('price') or 0,
                'consumer_price': int(n.get('fixedPrice') or 0),
                'shipping_fee': n.get('shippingFee') or 0,
                'shipping_type': n.get('shippingType') or '',
                'image_large': images[0] if images else '',
                'manufacturer': n.get('production') or '',
                'origin': n.get('origin') or '',
            })
            new_rows.append((code, data, STATUS_MAP.get(n.get('status'), 1)))
        _log(log_fn, f'  {page}페이지 처리 — 누적 스캔 {scanned:,}건, 신규발견 {len(new_rows):,}건')

        empty_streak = empty_streak + 1 if new_in_page == 0 else 0
        if page > 1 and empty_streak >= 2:
            _log(log_fn, f'  신규 0건 페이지 {empty_streak}회 연속 — dateDesc 정렬상 이후는 전부 기존 상품으로 판단해 조기 종료')
            break
        if not result['pageInfo']['hasNextPage'] or (max_pages and page >= max_pages):
            break
        after = result['pageInfo']['endCursor']

    if new_rows:
        all_cols = ['product_code'] + fields + orig_fields + ['sale_status', 'is_synced', 'uploaded_at']
        placeholders = ', '.join(['%s'] * len(all_cols))
        insert_sql = f"INSERT INTO ownerclan_product ({', '.join(all_cols)}) VALUES ({placeholders})"
        with connections['default'].cursor() as cur:
            for code, data, sale_status in new_rows:
                vals = [code] + [data[f] for f in fields] + [data[f] for f in fields] + [sale_status, 1, now]
                cur.execute(insert_sql, vals)
    _log(log_fn, f'[ownerclan-api:{account.login_id}] 완료 — 신규 {len(new_rows):,}건 추가 (총 스캔 {scanned:,}건)')

    account.last_synced_at = timezone.now()
    account.last_new_count = len(new_rows)
    account.save(update_fields=['last_synced_at', 'last_new_count'])
    return {'new': len(new_rows), 'scanned': scanned}
