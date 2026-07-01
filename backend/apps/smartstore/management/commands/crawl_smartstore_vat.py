from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '스마트스토어 부가세신고내역(매출) 크롤링 → TaxVatMonthly 저장'

    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*', help='특정 계정만 (login_id)')
        parser.add_argument('--start', help='시작 YYYYMM (예: 202601)')
        parser.add_argument('--end', help='종료 YYYYMM (예: 202605)')
        parser.add_argument('--no-save', action='store_true', help='DB 저장 없이 출력만')

    def handle(self, *args, **options):
        from crawlers.smartstore_vat_crawler import run_vat_accounts
        result = run_vat_accounts(
            account_filter=options.get('accounts'),
            start_ym=options.get('start'),
            end_ym=options.get('end'),
            log_fn=lambda msg: self.stdout.write(msg),
            save=not options.get('no_save', False),
        )
        self.stdout.write(self.style.SUCCESS(f'완료: {result}'))
