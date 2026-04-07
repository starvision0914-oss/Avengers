from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '지마켓 프라임 입찰기간 변경'

    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*')
        parser.add_argument('--source', default='manual')

    def handle(self, *args, **options):
        from crawlers.gmarket_cpp_crawler import run_all_accounts
        result = run_all_accounts(
            log_fn=lambda m: self.stdout.write(m),
            account_filter=options.get('accounts'),
            source=options.get('source', 'manual'),
        )
        self.stdout.write(self.style.SUCCESS(str(result)))
