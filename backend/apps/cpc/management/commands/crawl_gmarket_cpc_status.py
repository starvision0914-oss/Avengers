from django.core.management.base import BaseCommand
class Command(BaseCommand):
    help = '지마켓 간편/일반광고 상태 수집'
    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*')
    def handle(self, *args, **options):
        from crawlers.gmarket_cpc_status_crawler import run_all_accounts
        result = run_all_accounts(log_fn=lambda m: self.stdout.write(m), account_filter=options.get('accounts'))
        self.stdout.write(self.style.SUCCESS(str(result)))
