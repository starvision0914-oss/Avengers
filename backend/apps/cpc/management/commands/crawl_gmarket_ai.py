from django.core.management.base import BaseCommand
class Command(BaseCommand):
    help = '지마켓 AI 광고 상태 크롤링'
    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*')
    def handle(self, *args, **options):
        from crawlers.gmarket_ai_crawler import run_all_accounts
        result = run_all_accounts(log_fn=lambda m: self.stdout.write(m), account_filter=options.get('accounts'))
        self.stdout.write(self.style.SUCCESS(str(result)))
