"""쿠팡 오픈API로 등록상품 동기화.

사용법:
  python manage.py sync_coupang_products              # 전 계정
  python manage.py sync_coupang_products --account rejoice678
"""
from django.core.management.base import BaseCommand

from apps.coupang.models import CoupangAccount
from apps.coupang.services import fetch_products, save_products


class Command(BaseCommand):
    help = '쿠팡 오픈API 등록상품 동기화'

    def add_arguments(self, parser):
        parser.add_argument('--account', help='특정 login_id만')

    def handle(self, *args, **options):
        qs = CoupangAccount.objects.filter(is_active=True)
        if options.get('account'):
            qs = qs.filter(login_id=options['account'])
        accounts = [a for a in qs.order_by('display_order', 'id') if a.has_api_key]
        self.stdout.write(f'[쿠팡] 상품 동기화 대상 {len(accounts)}개')

        total = 0
        for acct in accounts:
            try:
                products = fetch_products(acct, log_fn=lambda m: self.stdout.write(m))
                saved = save_products(acct, products)
                total += saved
                self.stdout.write(self.style.SUCCESS(f'[쿠팡:{acct.login_id}] {saved}건 저장'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'[쿠팡:{acct.login_id}] 오류: {e}'))

        self.stdout.write(self.style.SUCCESS(f'[쿠팡] 총 {total}건 저장'))
