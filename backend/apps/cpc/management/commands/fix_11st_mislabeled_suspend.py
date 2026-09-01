"""2026-09-01 새벽 버그 정리용 1회성 커맨드.
suspend_11st_confirmed_soldout의 이전 버그로, 실제로는 11번가에서 손대지 않았는데
DB에서만 '판매중지'로 잘못 찍힌 상품들(성공 14개 계정 제외 전체, W코드)을 오너클랜에
다시 조회해서:
  - 오너클랜에서 지금 '판매가능'으로 나오면 → 진짜 문제(방치하면 영영 재검토 안 됨) →
    '품절'로 되돌려서 다음 sync_11st_ownerclan_stock 실행 때 정상적으로 재검토되게 함.
  - 오너클랜에서도 여전히 품절/미확인이면 → 라벨만 다를 뿐 사실상 결과는 같으므로(둘 다
    '판매불가' 의미) 그대로 둠 — 괜히 원래부터 있던 정상 판매중지까지 잘못 건드릴 위험 방지.

사용법: python manage.py fix_11st_mislabeled_suspend [--dry-run]
"""
import time

from django.core.management.base import BaseCommand


SUCCESS_ACCOUNTS_2026_09_01 = [
    'dlrmsgh012', 'dlrmsgh013', 'dlrmsgh7942', 'dlrmsgh7943', 'jinag7462',
    'rejoice119', 'rejoice1231', 'rejoice1234', 'rejoice321', 'rejoice345',
    'rejoice44', 'rejoice567', 'rejoice666', 'rejoice794',
]


class Command(BaseCommand):
    help = "suspend_11st_confirmed_soldout 버그로 잘못 판매중지 표시된 항목 중 실제 판매가능한 것만 품절로 복구"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--oc-account', default='rejoice999')
        parser.add_argument('--chunk', type=int, default=50)

    def handle(self, *args, **opts):
        import requests
        from apps.cpc.models import ElevenMyProduct
        from apps.ownerclan.models import OwnerclanApiAccount
        from crawlers.ownerclan_api_crawler import _get_token, API_URL

        dry_run = opts['dry_run']
        chunk_size = opts['chunk']

        oc_acc = OwnerclanApiAccount.objects.filter(login_id=opts['oc_account'], is_active=True).first()
        oc_token = _get_token(oc_acc)
        oc_headers = {'Authorization': f'Bearer {oc_token}'}

        qs = ElevenMyProduct.objects.filter(
            status_type='판매중지', seller_product_code__regex=r'^W[0-9A-Fa-f]+$'
        ).exclude(account__login_id__in=SUCCESS_ACCOUNTS_2026_09_01)
        products = list(qs)
        self.stdout.write(f'점검 대상(오표시 의심): {len(products)}건')

        def oc_lookup(codes):
            keys_str = ', '.join(f'"{c}"' for c in codes)
            query = f'query {{ itemsByKeys(keys: [{keys_str}]) {{ key status options {{ status quantity }} }} }}'
            for attempt in range(3):
                try:
                    r = requests.get(API_URL, params={'query': query}, headers=oc_headers, timeout=45)
                    r.raise_for_status()
                    return {it['key']: it for it in (r.json().get('data', {}).get('itemsByKeys') or []) if it}
                except Exception:
                    if attempt == 2:
                        return None
                    time.sleep(3)

        to_revert_ids = []
        checked = 0
        for i in range(0, len(products), chunk_size):
            batch = products[i:i + chunk_size]
            codes = [p.seller_product_code for p in batch]
            oc_map = oc_lookup(codes)
            if oc_map is None:
                continue
            for p in batch:
                oc_item = oc_map.get(p.seller_product_code)
                checked += 1
                if oc_item and oc_item.get('status') == 'available':
                    has_stock_option = any(
                        (o.get('status') == 'available' and (o.get('quantity') or 0) > 0)
                        for o in (oc_item.get('options') or [])
                    )
                    if has_stock_option:
                        to_revert_ids.append(p.pk)
            if i % (chunk_size * 20) == 0:
                self.stdout.write(f'진행 {min(i+chunk_size, len(products))}/{len(products)} (되돌릴대상 누적 {len(to_revert_ids)})', )

        self.stdout.write(f'=== 점검완료: {checked}건 확인, 실제 판매가능한데 오표시된 것 {len(to_revert_ids)}건 ===')

        if to_revert_ids and not dry_run:
            ElevenMyProduct.objects.filter(pk__in=to_revert_ids).update(status_type='품절')
            self.stdout.write(self.style.SUCCESS(f'{len(to_revert_ids)}건 "품절"로 복구 완료 (다음 sync_11st_ownerclan_stock 실행시 정상적으로 판매중 전환될 것)'))
        elif dry_run:
            self.stdout.write('(dry-run — 실제 반영 없음)')
