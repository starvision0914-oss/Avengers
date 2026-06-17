"""11번가 기간별 보고서(일자별 27컬럼) → 계정별 구글시트 업로드.
매월 1일=전월 / 그 외=당월. 누락 날짜는 빈행으로 채움.
사용: python manage.py crawl_11st_period_gsheet [--accounts id1 id2] [--no-gsheet]
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '11번가 기간별 보고서(일자별 27컬럼) → 구글시트 업로드 (1일=전월/그외=당월)'

    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*', help='특정 login_id 만')
        parser.add_argument('--no-gsheet', action='store_true', help='시트 업로드 없이 수집만(점검용)')

    def handle(self, *args, **options):
        from crawlers.eleven_period_report import run_all_accounts
        res = run_all_accounts(
            log_fn=lambda m: self.stdout.write(m),
            account_filter=options.get('accounts'),
            gsheet=not options.get('no_gsheet', False),
        )
        self.stdout.write(str(res))
