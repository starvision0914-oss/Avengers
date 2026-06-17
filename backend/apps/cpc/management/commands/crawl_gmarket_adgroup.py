"""지마켓 CPC 광고그룹별 성과 수집 — GmarketAdGroupPerf."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '지마켓 CPC 광고그룹별 성과(노출/클릭/광고비) 수집'

    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*', help='특정 계정만 수집')

    def handle(self, *args, **options):
        from crawlers.gmarket_adgroup_crawler import run_all_accounts
        res = run_all_accounts(log_fn=lambda m: self.stdout.write(m),
                               account_filter=options.get('accounts'))
        self.stdout.write(self.style.SUCCESS(f'완료: {res}'))
