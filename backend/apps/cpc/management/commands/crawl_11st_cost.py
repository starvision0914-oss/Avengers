from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = '11번가 광고비 크롤링'

    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*', help='특정 계정만 수집')

    def handle(self, *args, **options):
        from crawlers.eleven_crawler import run_all_accounts
        result = run_all_accounts(
            log_fn=lambda msg: self.stdout.write(msg),
            account_filter=options.get('accounts'),
        )
        self.stdout.write(self.style.SUCCESS(f'완료: {result}'))
