"""스마트스토어 상품의 판매상태(품절/판매중)를 오너클랜 실재고 기준으로 정정.

배경: 스마트스토어 자체 stockQuantity/statusType이 어떤 이유로든(수동조작, 동기화 누락 등)
실제 공급사(오너클랜) 재고와 어긋나는 경우가 있다(예: 옵션 4개 전부 재고 9999인데
상품 statusType만 OUTOFSTOCK으로 얼어붙어 있던 사례, 2026-08-30 실측).

오너클랜 GraphQL itemsByKeys로 W코드 배치조회 → 옵션별(sellerManagerCode↔key) status/quantity를
스마트스토어 optionCombinations에 반영 → 옵션이 하나라도 판매가능하면 상품 statusType=SALE,
전부 불가면 OUTOFSTOCK.

사용법:
  python manage.py sync_ownerclan_stock --status OUTOFSTOCK --limit 200 --dry-run
  python manage.py sync_ownerclan_stock --status OUTOFSTOCK
  python manage.py sync_ownerclan_stock --account-id 3
"""
import time

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '스마트스토어 상품 판매상태를 오너클랜 실재고 기준으로 동기화'

    def add_arguments(self, parser):
        parser.add_argument('--status', default='OUTOFSTOCK', help='대상 status_type (기본 OUTOFSTOCK)')
        parser.add_argument('--account-id', type=int, help='특정 계정만')
        parser.add_argument('--limit', type=int, default=0, help='0=전체')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--chunk', type=int, default=50, help='오너클랜 배치조회 1회당 W코드 수')
        parser.add_argument('--oc-account', default='dlwodbs999', help='사용할 오너클랜 API 계정 login_id')

    def handle(self, *args, **opts):
        import requests
        from apps.smartstore.models import SmartStoreProduct
        from apps.smartstore.services.naver_api import _get_access_token, sync_stock_from_ownerclan
        from apps.ownerclan.models import OwnerclanApiAccount
        from crawlers.ownerclan_api_crawler import _get_token, API_URL

        dry_run = opts['dry_run']
        chunk_size = opts['chunk']

        oc_acc = OwnerclanApiAccount.objects.filter(login_id=opts['oc_account'], is_active=True).first()
        if not oc_acc:
            self.stderr.write('오너클랜 API 계정 없음')
            return
        oc_token = _get_token(oc_acc)
        oc_headers = {'Authorization': f'Bearer {oc_token}'}

        qs = SmartStoreProduct.objects.filter(status_type=opts['status']).exclude(seller_management_code='')
        qs = qs.filter(seller_management_code__regex=r'^W[0-9A-F]+$')
        if opts['account_id']:
            qs = qs.filter(account_id=opts['account_id'])
        qs = qs.select_related('account').order_by('id')
        if opts['limit']:
            qs = qs[:opts['limit']]

        products = list(qs)
        self.stdout.write(f'대상: {len(products)}건 (status={opts["status"]})')

        naver_tokens = {}  # account_id -> (token, issued_at)

        def get_naver_token(acc):
            entry = naver_tokens.get(acc.id)
            if entry and time.time() - entry[1] < 900:
                return entry[0]
            token = _get_access_token(acc.commerce_api_key, acc.commerce_secret_key)
            naver_tokens[acc.id] = (token, time.time())
            return token

        fixed = 0
        unchanged = 0
        no_match = 0
        errors = 0

        for i in range(0, len(products), chunk_size):
            batch = products[i:i + chunk_size]
            codes = [p.seller_management_code for p in batch]
            keys_str = ', '.join(f'"{c}"' for c in codes)
            query = f'query {{ itemsByKeys(keys: [{keys_str}]) {{ key status options {{ key quantity status optionAttributes {{ name value }} }} }} }}'
            items = None
            for attempt in range(3):
                try:
                    r = requests.get(API_URL, params={'query': query}, headers=oc_headers, timeout=45)
                    r.raise_for_status()
                    items = r.json().get('data', {}).get('itemsByKeys', []) or []
                    break
                except Exception as e:
                    if attempt == 2:
                        self.stderr.write(f'오너클랜 배치조회 실패({i}): {e}')
                    else:
                        time.sleep(3)
            if items is None:
                errors += len(batch)
                continue

            by_key = {it['key']: it for it in items if it}

            for p in batch:
                oc_item = by_key.get(p.seller_management_code)
                if not oc_item:
                    no_match += 1
                    continue
                if oc_item.get('status') != 'available':
                    unchanged += 1  # 오너클랜도 품절 — 그대로 둠(정상)
                    continue
                try:
                    if dry_run:
                        has_stock_option = any(
                            o.get('status') == 'available' and (o.get('quantity') or 0) > 0
                            for o in (oc_item.get('options') or [])
                        )
                        if has_stock_option:
                            fixed += 1
                            self.stdout.write(f'[dry-run] {p.account.store_name} {p.seller_management_code} {p.name[:30]} → SALE 예정')
                        else:
                            unchanged += 1
                        continue

                    token = get_naver_token(p.account)
                    result = sync_stock_from_ownerclan(p.channel_product_no, token, oc_item)
                    if result['changed']:
                        SmartStoreProduct.objects.filter(pk=p.pk).update(status_type=result['new_status'])
                        fixed += 1
                        self.stdout.write(f'{p.account.store_name} {p.seller_management_code} {p.name[:30]} → {result["new_status"]} ({len(result["detail"])}개 옵션 변경)')
                    else:
                        unchanged += 1
                except Exception as e:
                    errors += 1
                    msg = str(e)
                    if '401' in msg:
                        naver_tokens.pop(p.account_id, None)
                    self.stderr.write(f'실패: {p.account.store_name} {p.seller_management_code}: {msg[:200]}')
                time.sleep(0.3)

            self.stdout.write(f'진행 {min(i + chunk_size, len(products))}/{len(products)} (수정{fixed}/변경없음{unchanged}/미매칭{no_match}/오류{errors})', ending='\n')
            time.sleep(0.5)

        self.stdout.write(self.style.SUCCESS(
            f'=== 완료: 수정(품절→판매중) {fixed} / 변경없음(오너클랜도 품절) {unchanged} / 오너클랜 미매칭 {no_match} / 오류 {errors} ==='
        ))
