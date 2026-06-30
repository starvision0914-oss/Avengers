"""스타비젼 상품명 JSON → 네이버 커머스 API 일괄 적용"""
import json
import time
import sys
from django.core.management.base import BaseCommand
import requests
from apps.smartstore.models import SmartStoreAccount
from apps.smartstore.services.naver_api import _get_access_token

INPUT = '/tmp/starvision_products.json'
OUTPUT_LOG = '/tmp/apply_log.json'
DELAY = 1.2


class Command(BaseCommand):
    help = '스타비젼 상품명 JSON → API 일괄 적용'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='new_name이 있는 모든 상품 (변경 없어도)')
        parser.add_argument('--dry-run', action='store_true', help='실제 PUT 없이 대상 목록만 출력')

    def handle(self, *args, **options):
        with open(INPUT) as f:
            d = json.load(f)

        only_changed = not options['all']
        targets = [
            p for p in d['products']
            if p.get('new_name') and (not only_changed or p['new_name'] != p['current_name'])
        ]
        self.stdout.write(f'적용 대상: {len(targets)}개 (only_changed={only_changed})')

        if options['dry_run']:
            for p in targets[:10]:
                self.stdout.write(f'  [{p["channel_product_no"]}] {p["current_name"]} → {p["new_name"]}')
            self.stdout.write(f'  ... (총 {len(targets)}개)')
            return

        acc = SmartStoreAccount.objects.get(login_id='dlrmsgh01234@gmail.com')
        token = _get_access_token(acc.commerce_api_key, acc.commerce_secret_key)
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

        success = []
        failed = []

        for i, p in enumerate(targets):
            if i > 0 and i % 150 == 0:
                token = _get_access_token(acc.commerce_api_key, acc.commerce_secret_key)
                headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
                self.stdout.write(f'  토큰 갱신')

            cno = p['channel_product_no']
            new_name = p['new_name']

            # GET
            r = None
            for attempt in range(4):
                r = requests.get(
                    f'https://api.commerce.naver.com/external/v2/products/channel-products/{cno}',
                    headers={'Authorization': headers['Authorization']}, timeout=20
                )
                if r.status_code == 200:
                    break
                if r.status_code == 429:
                    time.sleep(3 + attempt * 3)
                else:
                    break

            if not r or r.status_code != 200:
                failed.append({'cno': cno, 'error': f'GET {r.status_code if r else "no_resp"}', 'name': p['current_name']})
                time.sleep(DELAY)
                continue

            data = r.json()
            op = data.get('originProduct', {})
            op['name'] = new_name
            op['statusType'] = 'SALE'

            # PUT
            pr = None
            for attempt in range(4):
                pr = requests.put(
                    f'https://api.commerce.naver.com/external/v2/products/channel-products/{cno}',
                    headers=headers,
                    json={'originProduct': op, 'smartstoreChannelProduct': data.get('smartstoreChannelProduct', {})},
                    timeout=20
                )
                if pr.status_code == 200:
                    break
                if pr.status_code == 429:
                    time.sleep(3 + attempt * 3)
                else:
                    break

            if pr and pr.status_code == 200:
                success.append(cno)
            else:
                failed.append({
                    'cno': cno,
                    'error': pr.status_code if pr else 'no_resp',
                    'msg': pr.text[:150] if pr else '',
                    'name': p['current_name'],
                    'new': new_name,
                })

            if (i + 1) % 50 == 0:
                self.stdout.write(f'  [{i+1}/{len(targets)}] 성공={len(success)}, 실패={len(failed)}')
                with open(OUTPUT_LOG, 'w') as lf:
                    json.dump({'success': success, 'failed': failed}, lf, ensure_ascii=False, indent=2)

            time.sleep(DELAY)

        with open(OUTPUT_LOG, 'w') as lf:
            json.dump({'success': success, 'failed': failed}, lf, ensure_ascii=False, indent=2)

        self.stdout.write(f'\n완료: 성공={len(success)}, 실패={len(failed)}')
        if failed:
            self.stdout.write('실패 샘플:')
            for f in failed[:5]:
                self.stdout.write(f'  {f}')
        self.stdout.write(f'로그: {OUTPUT_LOG}')
