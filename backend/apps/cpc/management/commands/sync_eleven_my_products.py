import json

from django.core.management.base import BaseCommand

from apps.cpc import eleven_my_product_service as svc


class Command(BaseCommand):
    help = '11번가 나의 상품 동기화 (집중관리 계정)'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='집중관리 ON 계정 모두')
        parser.add_argument('--api-all', action='store_true', help='api_key 보유 전체 활성계정(상태 정기갱신용)')
        parser.add_argument('--account-id', type=int, default=None, help='특정 CrawlerAccount id')

    def handle(self, *args, **opts):
        def log(msg):
            self.stdout.write(msg)
            self.stdout.flush()

        if opts['account_id']:
            result = svc.sync_products_for_account(opts['account_id'], log_fn=log)
        elif opts['api_all']:
            result = svc.sync_focused_accounts(log_fn=log, focused_only=False)
        elif opts['all']:
            result = svc.sync_focused_accounts(log_fn=log)
        else:
            self.stderr.write('--all / --api-all / --account-id <id> 중 하나 필요')
            return

        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
