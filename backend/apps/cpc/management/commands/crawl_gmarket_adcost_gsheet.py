"""지마켓 상품별 광고비(GmarketProductAdCost) → 계정별 구글시트 업로드.
AI/CPC 분리 스프레드시트, 워크시트=계정ID. 1일=전월 / 그외=당월.
상품별 광고비 크롤(crawl_gmarket_ad_report) 직후 호출(매일 08:00 cron).

사용:
  python manage.py crawl_gmarket_adcost_gsheet                 # 자동기간, 전체 계정
  python manage.py crawl_gmarket_adcost_gsheet --accounts a b  # 특정 계정만
  python manage.py crawl_gmarket_adcost_gsheet --year 2026 --month 5
  python manage.py crawl_gmarket_adcost_gsheet --no-gsheet     # 업로드 없이 점검만
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '지마켓 상품별 광고비 → 구글시트 업로드 (AI/CPC 분리, 1일=전월/그외=당월)'

    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*', help='특정 login_id 만')
        parser.add_argument('--year', type=int, default=None)
        parser.add_argument('--month', type=int, default=None)
        parser.add_argument('--no-gsheet', action='store_true', help='업로드 없이 점검만')

    def handle(self, *args, **o):
        from crawlers.gmarket_adcost_gsheet import run_all_accounts
        res = run_all_accounts(
            log_fn=lambda m: self.stdout.write(m),
            account_filter=o.get('accounts'),
            gsheet=not o.get('no_gsheet', False),
            year=o.get('year'),
            month=o.get('month'),
        )
        self.stdout.write(self.style.SUCCESS(str(res)))
