"""스타비젼 상품 데이터 수집 → JSON 저장 (상품명 최적화용)"""
import time
import json
import sys
from django.core.management.base import BaseCommand
import requests
from apps.smartstore.models import SmartStoreAccount, SmartStoreProduct
from apps.smartstore.services.naver_api import _get_access_token

OUTPUT = '/tmp/starvision_products.json'
DELAY = 1.0  # 429 방지: 초당 1건


class Command(BaseCommand):
    help = '스타비젼 SALE 상품 데이터 수집'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0)
        parser.add_argument('--offset', type=int, default=0)

    def handle(self, *args, **options):
        acc = SmartStoreAccount.objects.get(login_id='dlrmsgh01234@gmail.com')
        token = _get_access_token(acc.commerce_api_key, acc.commerce_secret_key)
        headers = {'Authorization': f'Bearer {token}'}

        qs = SmartStoreProduct.objects.filter(account=acc, status_type='SALE').order_by('id')
        offset = options['offset']
        limit = options['limit']
        if offset:
            qs = qs[offset:]
        if limit:
            qs = qs[:limit]

        products = list(qs.values('id', 'channel_product_no', 'name', 'category_id', 'seller_management_code'))
        total = len(products)
        self.stdout.write(f'수집 대상: {total}개')

        results = []
        errors = []
        token_refresh_interval = 200  # 200개마다 토큰 갱신

        for i, p in enumerate(products):
            if i > 0 and i % token_refresh_interval == 0:
                token = _get_access_token(acc.commerce_api_key, acc.commerce_secret_key)
                headers = {'Authorization': f'Bearer {token}'}
                self.stdout.write(f'  토큰 갱신')

            cno = p['channel_product_no']
            try:
                r = None
                for attempt in range(4):
                    r = requests.get(
                        f'https://api.commerce.naver.com/external/v2/products/channel-products/{cno}',
                        headers=headers, timeout=20
                    )
                    if r.status_code == 200:
                        break
                    if r.status_code == 429:
                        time.sleep(3 + attempt * 3)
                        continue
                    break
                if r is None or r.status_code != 200:
                    errors.append({'cno': cno, 'error': r.status_code if r else 'no_response', 'name': p['name']})
                    continue

                d = r.json()
                op = d.get('originProduct', {})
                da = op.get('detailAttribute', {})
                oi = da.get('optionInfo', {})
                nss = da.get('naverShoppingSearchInfo', {})

                options_list = [
                    c.get('optionName1', '') for c in oi.get('optionCombinations', [])
                    if c.get('optionName1')
                ]
                # 중복 제거
                seen = set()
                unique_opts = [o for o in options_list if not (o in seen or seen.add(o))]

                results.append({
                    'db_id': p['id'],
                    'channel_product_no': cno,
                    'category_id': op.get('leafCategoryId', p['category_id']),
                    'current_name': op.get('name', p['name']),
                    'seller_code': p['seller_management_code'],
                    'options': unique_opts[:10],
                    'brand': nss.get('brandName', ''),
                    'manufacturer': nss.get('manufacturerName', ''),
                    'model_name': nss.get('modelName', ''),
                    'status': op.get('statusType', 'SALE'),
                    'new_name': '',  # AI가 채울 필드
                })

                if (i + 1) % 50 == 0:
                    self.stdout.write(f'  [{i+1}/{total}] 수집 중... 오류={len(errors)}')
                    # 중간 저장
                    with open(OUTPUT, 'w', encoding='utf-8') as f:
                        json.dump({'products': results, 'errors': errors, 'total': total}, f,
                                  ensure_ascii=False, indent=2)

            except Exception as e:
                errors.append({'cno': cno, 'error': str(e), 'name': p['name']})

            time.sleep(DELAY)

        with open(OUTPUT, 'w', encoding='utf-8') as f:
            json.dump({'products': results, 'errors': errors, 'total': total}, f,
                      ensure_ascii=False, indent=2)

        self.stdout.write(f'\n완료: 수집={len(results)}, 오류={len(errors)}')
        self.stdout.write(f'저장: {OUTPUT}')
