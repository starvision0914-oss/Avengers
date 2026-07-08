from datetime import datetime

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '롯데온 광고비/상품별광고비 크롤링 (광고주센터 클릭광고 리포트)'

    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*', help='특정 계정만 수집')
        parser.add_argument('--start-date', help='YYYY-MM-DD (미지정 시 최근 7일)')
        parser.add_argument('--end-date', help='YYYY-MM-DD (미지정 시 오늘)')

    def handle(self, *args, **options):
        from crawlers.lotteon_ad_crawler import run_all_accounts
        start_date = None
        end_date = None
        if options.get('start_date'):
            start_date = datetime.strptime(options['start_date'], '%Y-%m-%d').date()
        if options.get('end_date'):
            end_date = datetime.strptime(options['end_date'], '%Y-%m-%d').date()
        result = run_all_accounts(
            log_fn=lambda msg: self.stdout.write(msg),
            account_filter=options.get('accounts'),
            start_date=start_date,
            end_date=end_date,
        )
        self.stdout.write(self.style.SUCCESS(f'완료: {result}'))
