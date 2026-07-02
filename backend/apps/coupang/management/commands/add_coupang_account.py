"""쿠팡 Wing 계정 등록 — ID/비번만 넣으면 세팅 끝.

사용법:
  python manage.py add_coupang_account --login-id abc123 --login-pw '비번' --seller-name "OO몰"
  python manage.py add_coupang_account --login-id abc123 --login-pw '비번' --rocket-growth
"""
from django.core.management.base import BaseCommand

from apps.coupang.models import CoupangAccount


class Command(BaseCommand):
    help = '쿠팡 Wing 계정 등록/갱신'

    def add_arguments(self, parser):
        parser.add_argument('--login-id', required=True)
        parser.add_argument('--login-pw', required=True)
        parser.add_argument('--seller-name', default='')
        parser.add_argument('--rocket-growth', action='store_true', help='로켓그로스 사용 계정')

    def handle(self, *args, **options):
        account, created = CoupangAccount.objects.update_or_create(
            login_id=options['login_id'],
            defaults={
                'login_pw': options['login_pw'],
                'seller_name': options['seller_name'] or options['login_id'],
                'is_rocket_growth': options['rocket_growth'],
                'is_active': True,
            },
        )
        verb = '등록' if created else '갱신'
        self.stdout.write(self.style.SUCCESS(
            f'{verb} 완료: {account.login_id} ({account.seller_name}) '
            f'로켓그로스={account.is_rocket_growth}'))
