from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '11번가 adoffice 일별 상품코드별 ROAS 누적 수집 (기본: 2026-01-01~어제)'

    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*')
        parser.add_argument('--from', dest='date_from', help='YYYY-MM-DD')
        parser.add_argument('--to', dest='date_to', help='YYYY-MM-DD')
        parser.add_argument('--with-gsheet', action='store_true',
                            help='같은 adoffice 세션에서 기간별 보고서까지 받아 구글시트 업로드(로그인 1회 통합)')
        parser.add_argument('--focused', action='store_true',
                            help='집중관리(is_focused) 계정만 수집')

    def handle(self, *args, **options):
        from crawlers.eleven_product_daily import run_all_accounts
        acct_filter = options.get('accounts')
        if options.get('focused') and not acct_filter:
            from apps.cpc.models import CrawlerAccount
            acct_filter = list(CrawlerAccount.objects.filter(
                platform='11st', is_active=True, is_focused=True
            ).values_list('login_id', flat=True))
            self.stdout.write(f'집중관리(is_focused) {len(acct_filter)}계정만 수집')
        res = run_all_accounts(
            log_fn=lambda m: self.stdout.write(m),
            account_filter=acct_filter,
            date_from=options.get('date_from'),
            date_to=options.get('date_to'),
            with_gsheet=options.get('with_gsheet', False),
        )
        self.stdout.write(str(res))
