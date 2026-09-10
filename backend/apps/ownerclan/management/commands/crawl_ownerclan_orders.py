from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '오너클랜 주문/배송조회(orderList.php) 엑셀다운로드/플레이오토 송장 정보 전 계정 순차 수집'

    def add_arguments(self, parser):
        parser.add_argument('--type', choices=['invoice', 'excel'], default='invoice')
        parser.add_argument('--accounts', default=None, help='콤마구분 login_id, 생략시 전체')

    def handle(self, *args, **options):
        from crawlers.ownerclan_web_crawler import run_order_download_all

        account_filter = options['accounts'].split(',') if options.get('accounts') else None
        results = run_order_download_all(
            file_type=options['type'], account_filter=account_filter,
            log_fn=lambda m: self.stdout.write(m))
        ok = sum(1 for r in results.values() if r.get('ok'))
        self.stdout.write(self.style.SUCCESS(f'완료: {ok}/{len(results)}'))
