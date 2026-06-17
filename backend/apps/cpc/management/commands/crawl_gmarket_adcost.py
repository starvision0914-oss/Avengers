"""지마켓/옥션(ESM) 광고비 수집 — 판매예치금 거래내역(GmarketCostHistory)."""
from datetime import datetime
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '지마켓/옥션 ESM 광고비(판매예치금 거래내역) 수집'

    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*', help='특정 계정만')
        parser.add_argument('--from', dest='date_from', default=None, help='YYYY-MM-DD')
        parser.add_argument('--to', dest='date_to', default=None, help='YYYY-MM-DD')

    def handle(self, *args, **o):
        from crawlers.gmarket_cost_crawler import run_all_accounts
        d0 = datetime.strptime(o['date_from'], '%Y-%m-%d').date() if o['date_from'] else None
        d1 = datetime.strptime(o['date_to'], '%Y-%m-%d').date() if o['date_to'] else None
        res = run_all_accounts(log_fn=lambda m: self.stdout.write(m),
                               account_filter=o.get('accounts'), date_from=d0, date_to=d1)
        self.stdout.write(self.style.SUCCESS(f'완료: {res}'))
