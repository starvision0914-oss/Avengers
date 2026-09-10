from django.core.management.base import BaseCommand
class Command(BaseCommand):
    help = '11번가 AI 캠페인 크롤링'
    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*')
        parser.add_argument('--scheduled', action='store_true',
                             help='예약 크롤(cron) — 다른 11번가 크롤이 돌고 있으면 락 풀릴 때까지 대기')
    def handle(self, *args, **options):
        from crawlers.eleven_ai_crawler import run_all_accounts
        result = run_all_accounts(log_fn=lambda m: self.stdout.write(m),
                                   account_filter=options.get('accounts'),
                                   scheduled=options.get('scheduled', False))
        self.stdout.write(self.style.SUCCESS(str(result)))
