"""예비상품(OwnerclanProduct, 판매중=sale_status 1) 전체를 오너클랜 라이브 API로 조회해
OwnerclanLiveStatus에 갱신 — sync_ownerclan_status.py(나의상품 W코드 순환점검)와 동일한
GraphQL 배치 조회 방식을 그대로 쓰되, 대상을 "나의상품에 걸린 W코드"가 아니라
"예비상품 전체(198K+)"로 바꾼 버전(2026-09-11, 사용자 요청 — 판매중 상품 전체 품절조사).

물량이 커서(사용자가 --all 지정 안 하면) 기본은 나의상품 점검과 동일하게 요일별 1/5 버킷으로
쪼갠다. 전체를 한 번에 돌리려면 --all(예상 7~8시간).

Usage:
    python3 manage.py sync_ownerclan_reserve_status --all
    python3 manage.py sync_ownerclan_reserve_status --bucket 2
"""
import time
import zlib
from datetime import datetime

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.ownerclan.models import OwnerclanApiAccount, OwnerclanProduct, OwnerclanLiveStatus
from crawlers.ownerclan_api_crawler import _get_token

URL = 'https://api.ownerclan.com/v1/graphql'
BATCH = 25


def _field_query(i, code):
    return (f'a{i}: item(key: "{code}") {{ key name price fixedPrice shippingFee '
            f'shippingType status production origin category {{ key fullName }} images(size: large) }}')


class Command(BaseCommand):
    help = '예비상품(판매중) 전체를 오너클랜 라이브 API로 조회 → OwnerclanLiveStatus 갱신'

    def add_arguments(self, parser):
        parser.add_argument('--bucket', type=int, default=None, help='0~4 강제 지정(기본: 오늘 요일)')
        parser.add_argument('--all', action='store_true', help='버킷 무시하고 전체 조회(예상 7~8시간)')
        parser.add_argument('--account', type=str, default='dlwodbs999')

    def handle(self, *args, **opts):
        acc = OwnerclanApiAccount.objects.get(login_id=opts['account'])
        token = _get_token(acc)
        if not token:
            self.stderr.write('토큰 발급 실패')
            return

        all_codes = sorted(OwnerclanProduct.objects.filter(sale_status=1)
                            .values_list('product_code', flat=True))
        if opts['all']:
            targets = all_codes
            self.stdout.write(f'[sync_ownerclan_reserve_status] 전체 모드 — 대상 {len(targets):,}건')
        else:
            bucket = opts['bucket'] if opts['bucket'] is not None else datetime.now().weekday()
            if bucket > 4:
                self.stdout.write(f'주말(weekday={bucket}) — 스킵')
                return
            targets = [c for c in all_codes if zlib.crc32(c.encode()) % 5 == bucket]
            self.stdout.write(f'[sync_ownerclan_reserve_status] 버킷 {bucket} — 전체 {len(all_codes):,}건 중 {len(targets):,}건')

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
        status_counts = {}

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
                    status_counts[status] = status_counts.get(status, 0) + 1
                    processed += 1
                    time.sleep(0.15)
            else:
                d = data.get('data') or {}
                for idx, c in enumerate(batch):
                    item = d.get(f'a{idx}')
                    status = item['status'] if item else 'NOT_FOUND'
                    upserts.append(OwnerclanLiveStatus(product_code=c, status=status, checked_at=now))
                    status_counts[status] = status_counts.get(status, 0) + 1
                    processed += 1
            if len(upserts) >= 500:
                flush()
            i += BATCH
            if (i // BATCH) % 40 == 0:
                elapsed = time.time() - t0
                rate = processed / elapsed if elapsed > 0 else 0
                eta = (len(targets) - processed) / rate / 60 if rate > 0 else 0
                self.stdout.write(f'{processed}/{len(targets)} 완료 — 경과 {elapsed/60:.1f}분 예상잔여 {eta:.1f}분 — {status_counts}')
            time.sleep(0.3)

        flush()
        elapsed = round(time.time() - t0, 1)
        self.stdout.write(f'[sync_ownerclan_reserve_status] 완료 — {processed:,}건, {elapsed/60:.1f}분 — {status_counts}')
