from django.core.management.base import BaseCommand
class Command(BaseCommand):
    help = '11번가 AI 캠페인 크롤링'
    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*')
    def handle(self, *args, **options):
        from crawlers.eleven_ai_crawler import run_all_accounts
        result = run_all_accounts(log_fn=lambda m: self.stdout.write(m), account_filter=options.get('accounts'))
        self.stdout.write(self.style.SUCCESS(str(result)))
