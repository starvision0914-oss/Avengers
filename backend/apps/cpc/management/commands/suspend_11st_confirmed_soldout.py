"""sync_11st_ownerclan_stock 다음 단계 — 여전히 '품절'인 W코드 상품 중
오너클랜에서 확인해봤을 때 (1) 진짜 품절이거나 (2) 오너클랜에 아예 없는(미매칭) 상품을
'판매중지'로 전환한다. 재고 있는 건 sync_11st_ownerclan_stock이 이미 판매중으로
바꿔놨을 것이므로, 이 시점에 남아있는 '품절'은 전부 대상.

주의: 11번가는 동시 크롤 금지(IP차단 방지, eleven_block_guard 전역락) — 이 커맨드는
반드시 sync_11st_ownerclan_stock이 완전히 끝난 뒤에만 실행할 것.

사용법:
  python manage.py suspend_11st_confirmed_soldout --dry-run
  python manage.py suspend_11st_confirmed_soldout
  python manage.py suspend_11st_confirmed_soldout --account tmxkqhrhksth000
"""
import time

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "오너클랜 확인 결과 품절/미매칭인 11번가 W코드 상품을 판매중지로 전환"

    def add_arguments(self, parser):
        parser.add_argument('--account', help='특정 11번가 login_id만')
        parser.add_argument('--oc-account', default='rejoice999', help='오너클랜 API 계정 login_id')
        parser.add_argument('--dry-run', action='store_true', help='실제 판매중지 없이 대상 목록만 출력')
        parser.add_argument('--chunk', type=int, default=50, help='오너클랜 배치조회 1회당 W코드 수')

    def handle(self, *args, **opts):
        import requests
        from apps.cpc.models import ElevenMyProduct, protected_login_ids
        from apps.ownerclan.models import OwnerclanApiAccount
        from crawlers.ownerclan_api_crawler import _get_token, API_URL

        dry_run = opts['dry_run']
        chunk_size = opts['chunk']

        oc_acc = OwnerclanApiAccount.objects.filter(login_id=opts['oc_account'], is_active=True).first()
        if not oc_acc:
            self.stderr.write(f'오너클랜 API 계정 없음: {opts["oc_account"]}')
            return
        oc_token = _get_token(oc_acc)
        oc_headers = {'Authorization': f'Bearer {oc_token}'}

        protected = protected_login_ids('11st')
        qs = ElevenMyProduct.objects.filter(
            status_type='품절', seller_product_code__regex=r'^W[0-9A-Fa-f]+$'
        ).exclude(account__login_id__in=protected)
        if opts['account']:
            qs = qs.filter(account__login_id=opts['account'])
        qs = qs.select_related('account').order_by('account_id', 'id')

        products = list(qs)
        self.stdout.write(f'검토 대상(현재도 품절): {len(products)}건')

        def oc_lookup(codes):
            keys_str = ', '.join(f'"{c}"' for c in codes)
            query = f'query {{ itemsByKeys(keys: [{keys_str}]) {{ key status }} }}'
            for attempt in range(3):
                try:
                    r = requests.get(API_URL, params={'query': query}, headers=oc_headers, timeout=45)
                    r.raise_for_status()
                    return {it['key']: it for it in (r.json().get('data', {}).get('itemsByKeys') or []) if it}
                except Exception:
                    if attempt == 2:
                        return None
                    time.sleep(3)

        to_suspend = []  # [{'login_id':..., 'product_no':...}]
        confirmed_soldout = 0
        unmatched = 0
        lookup_fail = 0

        for i in range(0, len(products), chunk_size):
            batch = products[i:i + chunk_size]
            codes = [p.seller_product_code for p in batch]
            oc_map = oc_lookup(codes)
            if oc_map is None:
                self.stderr.write(f'오너클랜 조회 실패({i}), 배치 스킵(판매중지 대상에서 제외 — 확인 안되면 손대지 않음)')
                lookup_fail += len(batch)
                continue
            for p in batch:
                oc_item = oc_map.get(p.seller_product_code)
                if not oc_item:
                    unmatched += 1
                    to_suspend.append({'login_id': p.account.login_id, 'product_no': p.product_no})
                elif oc_item.get('status') != 'available':
                    confirmed_soldout += 1
                    to_suspend.append({'login_id': p.account.login_id, 'product_no': p.product_no})
            if i % (chunk_size * 10) == 0:
                self.stdout.write(f'조회 진행 {min(i + chunk_size, len(products))}/{len(products)} (판매중지대상 누적 {len(to_suspend)})')

        self.stdout.write(
            f'판매중지 대상: {len(to_suspend)}건 (진짜품절 {confirmed_soldout} + 오너클랜미매칭 {unmatched}), '
            f'조회실패로제외 {lookup_fail}건'
        )

        if dry_run:
            for t in to_suspend[:50]:
                self.stdout.write(f'[dry-run] {t["login_id"]} {t["product_no"]} → 판매중지 예정')
            self.stdout.write('(dry-run — 실제 반영 없음)')
            return

        if not to_suspend:
            self.stdout.write('대상 없음, 종료')
            return

        from crawlers.eleven_suspend_only import suspend_only
        result = suspend_only(to_suspend, mode='real', log_fn=lambda m: self.stdout.write(m))
        self.stdout.write(self.style.SUCCESS(f'=== 완료: {result} ==='))

        # 실제 반영 성공분만 DB 상태도 판매중지로 동기화(다음날 크롤 전까지 대시보드 정합성 유지)
        product_nos = [t['product_no'] for t in to_suspend]
        ElevenMyProduct.objects.filter(product_no__in=product_nos, status_type='품절').update(status_type='판매중지')
