"""유진코리아몰(account_id=4) 상품명에 수량/스펙이 잘못 덧붙은 것(예: '120정', '1kg')을
원본(오너클랜) 상품명으로 되돌리는 1회성 수정 스크립트 (2026-09-16, 사용자요청).
대상: /tmp/yujin_korea_name_fix.json (channel_product_no, current_name, new_name)."""
import json
import time
from django.core.management.base import BaseCommand
from django.utils import timezone
import requests
from apps.smartstore.models import SmartStoreAccount, SmartStoreProduct, SmartStoreNameOptLog
from apps.smartstore.services.naver_api import _get_access_token

INPUT = '/tmp/yujin_korea_name_fix.json'
OUTPUT_LOG = '/tmp/yujin_korea_name_fix_result.json'
DELAY = 1.2


class Command(BaseCommand):
    help = '유진코리아몰 수량/스펙 오표기 상품명 원복(원본 오너클랜 상품명으로)'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='실제 PUT 없이 대상 목록만 출력')
        parser.add_argument('--limit', type=int, default=None, help='테스트용 상위 N건만')

    def handle(self, *args, **options):
        with open(INPUT, encoding='utf-8') as f:
            d = json.load(f)
        targets = d['products']
        if options.get('limit'):
            targets = targets[:options['limit']]
        self.stdout.write(f'적용 대상: {len(targets)}개')

        if options['dry_run']:
            for p in targets[:10]:
                self.stdout.write(f'  [{p["channel_product_no"]}] {p["current_name"]} → {p["new_name"]}')
            self.stdout.write(f'  ... (총 {len(targets)}개)')
            return

        acc = SmartStoreAccount.objects.get(id=4)
        token = _get_access_token(acc.commerce_api_key, acc.commerce_secret_key)
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

        success = []
        failed = []

        for i, p in enumerate(targets):
            if i > 0 and i % 150 == 0:
                token = _get_access_token(acc.commerce_api_key, acc.commerce_secret_key)
                headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
                self.stdout.write('  토큰 갱신')

            cno = p['channel_product_no']
            new_name = p['new_name']

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
            live_name = op.get('name', '')
            op['name'] = new_name
            op['statusType'] = 'SALE'

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
                SmartStoreProduct.objects.filter(account_id=4, channel_product_no=cno).update(
                    name=new_name, synced_at=timezone.now())
                SmartStoreNameOptLog.objects.create(
                    account_id=4, channel_product_no=cno, status='done',
                    fields_updated='name',
                    reason='수량/스펙 오표기(예: 24팩→120정) 원본 되돌림(사용자요청, 2026-09-16)',
                    old_name=live_name or p['current_name'], new_name=new_name,
                )
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
                with open(OUTPUT_LOG, 'w', encoding='utf-8') as lf:
                    json.dump({'success': success, 'failed': failed}, lf, ensure_ascii=False, indent=2)

            time.sleep(DELAY)

        with open(OUTPUT_LOG, 'w', encoding='utf-8') as lf:
            json.dump({'success': success, 'failed': failed}, lf, ensure_ascii=False, indent=2)

        self.stdout.write(f'\n완료: 성공={len(success)}, 실패={len(failed)}')
        if failed:
            self.stdout.write('실패 샘플:')
            for f in failed[:5]:
                self.stdout.write(f'  {f}')
        self.stdout.write(f'로그: {OUTPUT_LOG}')
