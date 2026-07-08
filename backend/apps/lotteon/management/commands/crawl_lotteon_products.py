from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '롯데온 나의 상품 크롤링 (판매자센터 세션 토큰 방식)'

    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*', help='특정 계정만 수집')

    def handle(self, *args, **options):
        from crawlers.lotteon_product_crawler import run_all_accounts
        result = run_all_accounts(
            log_fn=lambda msg: self.stdout.write(msg),
            account_filter=options.get('accounts'),
        )
        self.stdout.write(self.style.SUCCESS(f'완료: {result}'))
