"""쿠팡 등록상품 판매자관리코드(W코드) 백필 — 상품별 상세조회 API 필요(목록 API엔 없음).

사용법:
  python manage.py sync_coupang_seller_codes                    # 전 계정, 미수집분만
  python manage.py sync_coupang_seller_codes --account rejoice999
  python manage.py sync_coupang_seller_codes --all              # 이미 수집된 것도 재조회
"""
from django.core.management.base import BaseCommand

from apps.coupang.models import CoupangAccount
from apps.coupang.services import backfill_seller_codes


class Command(BaseCommand):
    help = '쿠팡 판매자관리코드(W코드) 백필'

    def add_arguments(self, parser):
        parser.add_argument('--account', help='특정 login_id만')
        parser.add_argument('--all', action='store_true', help='이미 값이 있는 것도 재조회')

    def handle(self, *args, **options):
        qs = CoupangAccount.objects.filter(is_active=True)
        if options.get('account'):
            qs = qs.filter(login_id=options['account'])
        accounts = [a for a in qs.order_by('display_order', 'id') if a.has_api_key]
        self.stdout.write(f'[쿠팡] 판매자관리코드 백필 대상 {len(accounts)}개 계정')

        total = 0
        for acct in accounts:
            try:
                updated = backfill_seller_codes(
                    acct, log_fn=lambda m: self.stdout.write(m),
                    only_missing=not options.get('all'),
                )
                total += updated
                self.stdout.write(self.style.SUCCESS(f'[쿠팡:{acct.login_id}] {updated}건 갱신'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'[쿠팡:{acct.login_id}] 오류: {e}'))

        self.stdout.write(self.style.SUCCESS(f'[쿠팡] 총 {total}건 갱신'))
