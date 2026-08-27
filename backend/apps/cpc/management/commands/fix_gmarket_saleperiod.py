"""지마켓 L코드 판매중 상품의 판매기간을 '설정안함'으로 일괄 변경.

사용법:
  python manage.py fix_gmarket_saleperiod --account rejoice234 --limit 100
  python manage.py fix_gmarket_saleperiod --all --limit 100   # 테스트
  python manage.py fix_gmarket_saleperiod --all               # 전체 실행(제한 없음)
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '지마켓 L코드 판매중 상품 판매기간을 설정안함으로 일괄 변경'

    def add_arguments(self, parser):
        parser.add_argument('--account', type=str, help='특정 계정 login_id')
        parser.add_argument('--all', action='store_true', help='활성 전체 계정')
        parser.add_argument('--limit', type=int, help='이번 실행에서 실제로 저장할 최대 건수(테스트용)')

    def handle(self, *args, **options):
        from crawlers.gmarket_saleperiod_fix import run_saleperiod_fix

        if options['account']:
            login_ids = [options['account']]
        elif options['all']:
            login_ids = None
        else:
            self.stdout.write(self.style.ERROR('--account 또는 --all 중 하나는 필요합니다'))
            return

        res = run_saleperiod_fix(login_ids=login_ids, limit=options['limit'],
                                  log_fn=lambda m: self.stdout.write(m))
        self.stdout.write(str(res))
