"""나의상품(지마켓/11번가/스마트스토어) 전체 W코드를 오너클랜 실제 API로 조회해 OwnerclanLiveStatus에 갱신.

가격(OwnerclanProduct/예비상품)과 무관하게 상태(판매중/품절/단종/존재안함)만 확인하는 용도.
전체 코드를 5개 버킷(월~금)으로 나눠 매일 1/5씩만 조회 — 하루 대상은
zlib.crc32(코드) % 5 로 결정되는 안정적 버킷(코드가 늘어나도 기존 코드의 요일은 안 바뀜).

Usage:
    python3 manage.py sync_ownerclan_status              # 오늘 요일(월=0..금=4) 버킷만
    python3 manage.py sync_ownerclan_status --bucket 2    # 특정 버킷 강제 지정
    python3 manage.py sync_ownerclan_status --all         # 전체(테스트/백필용, 매우 오래 걸림)
"""
import json
import re
import time
import zlib
from datetime import datetime

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.cpc.models import GmarketMyProduct, ElevenMyProduct
from apps.smartstore.models import SmartStoreProduct
from apps.ownerclan.models import OwnerclanApiAccount, OwnerclanLiveStatus
from crawlers.ownerclan_api_crawler import _get_token

URL = 'https://api.ownerclan.com/v1/graphql'
BATCH = 25
W_RE = re.compile(r'^(?:WDM_|AUTO_)?(W[0-9A-Za-z]{6})$', re.IGNORECASE)


def normalize(code):
    m = W_RE.match((code or '').strip())
    return m.group(1).upper() if m else None


def collect_all_codes():
    codes = set()
    for model, field in ((GmarketMyProduct, 'seller_product_code'),
                          (ElevenMyProduct, 'seller_product_code'),
                          (SmartStoreProduct, 'seller_management_code')):
        qs = model.objects.filter(**{f'{field}__startswith': 'W'}).values_list(field, flat=True).distinct()
        for c in qs.iterator():
            n = normalize(c)
            if n:
                codes.add(n)
    return codes


def _field_query(i, code):
    return (f'a{i}: item(key: "{code}") {{ key name price fixedPrice shippingFee '
            f'shippingType status production origin category {{ key fullName }} images(size: large) }}')


class Command(BaseCommand):
    help = '나의상품 W코드 전체를 오너클랜 라이브 API로 순환 조회 → OwnerclanLiveStatus 갱신(주5일 1/5씩)'

    def add_arguments(self, parser):
        parser.add_argument('--bucket', type=int, default=None, help='0~4 강제 지정(기본: 오늘 요일)')
        parser.add_argument('--all', action='store_true', help='버킷 무시하고 전체 조회(백필용)')
        parser.add_argument('--account', type=str, default='dlwodbs999')

    def handle(self, *args, **opts):
        acc = OwnerclanApiAccount.objects.get(login_id=opts['account'])
        token = _get_token(acc)
        if not token:
            self.stderr.write('토큰 발급 실패')
            return

        all_codes = sorted(collect_all_codes())
        if opts['all']:
            targets = all_codes
            self.stdout.write(f'[sync_ownerclan_status] 전체 모드 — 대상 {len(targets):,}건')
        else:
            bucket = opts['bucket'] if opts['bucket'] is not None else datetime.now().weekday()
            if bucket > 4:
                self.stdout.write(f'주말(weekday={bucket}) — 스킵')
                return
            targets = [c for c in all_codes if zlib.crc32(c.encode()) % 5 == bucket]
            self.stdout.write(f'[sync_ownerclan_status] 버킷 {bucket} — 전체 {len(all_codes):,}건 중 {len(targets):,}건')

        def run_query(batch_codes, retries=4):
            nonlocal token
            q = 'query {' + '\n'.join(_field_query(i, c) for i, c in enumerate(batch_codes)) + '}'
            for attempt in range(retries):
                try:
                    r = requests.get(URL, headers={'Authorization': f'Bearer {token}'},
                                      params={'query': q}, timeout=25)
                    if r.status_code == 401:
                        token = _get_token(acc)
                        continue
                    if r.status_code != 200:
                        time.sleep(2 * (attempt + 1))
                        continue
                    return r.json()
                except Exception:
                    time.sleep(2 * (attempt + 1))
            return None

        now = timezone.now()
        processed = 0
        t0 = time.time()
        i = 0
        upserts = []

        def flush():
            if not upserts:
                return
            OwnerclanLiveStatus.objects.bulk_create(
                upserts, update_conflicts=True,
                update_fields=['status', 'checked_at'], batch_size=1000)
            upserts.clear()

        while i < len(targets):
            batch = targets[i:i + BATCH]
            data = run_query(batch)
            if data is None or (data.get('errors') and not data.get('data')):
                for c in batch:
                    d1 = run_query([c])
                    item = (d1.get('data') or {}).get('a0') if d1 else None
                    status = item['status'] if item else 'NOT_FOUND'
                    upserts.append(OwnerclanLiveStatus(product_code=c, status=status, checked_at=now))
                    processed += 1
                    time.sleep(0.15)
            else:
                d = data.get('data') or {}
                for idx, c in enumerate(batch):
                    item = d.get(f'a{idx}')
                    status = item['status'] if item else 'NOT_FOUND'
                    upserts.append(OwnerclanLiveStatus(product_code=c, status=status, checked_at=now))
                    processed += 1
            if len(upserts) >= 500:
                flush()
            i += BATCH
            if (i // BATCH) % 40 == 0:
                elapsed = time.time() - t0
                rate = processed / elapsed if elapsed > 0 else 0
                eta = (len(targets) - processed) / rate / 60 if rate > 0 else 0
                self.stdout.write(f'{processed}/{len(targets)} 완료 — 경과 {elapsed/60:.1f}분 예상잔여 {eta:.1f}분')
            time.sleep(0.3)

        flush()
        elapsed = round(time.time() - t0, 1)
        self.stdout.write(f'[sync_ownerclan_status] 완료 — {processed:,}건, {elapsed/60:.1f}분')
