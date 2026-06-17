"""
11번가 셀러오피스 '내 상품' Selenium 크롤러 (OpenAPI 키 없는 계정용).

사용:
  python manage.py crawl_11st_products            # api_key 없는 모든 계정
  python manage.py crawl_11st_products --all      # api_key 유무와 관계없이 모든 활성 계정
  python manage.py crawl_11st_products --accounts user1 user2
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "11번가 셀러오피스 상품 Selenium 크롤링 (OpenAPI 키 미보유 계정용)"

    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*', help='특정 login_id 만 수집')
        parser.add_argument(
            '--all', action='store_true',
            help='api_key 보유 여부와 관계없이 모든 활성 11번가 계정 대상',
        )
        parser.add_argument(
            '--force', action='store_true',
            help='최근 수집(신선도) 스킵 무시하고 강제 재수집',
        )

    def handle(self, *args, **options):
        from crawlers.eleven_product_crawler import run_all_accounts
        result = run_all_accounts(
            log_fn=lambda msg: self.stdout.write(msg),
            account_filter=options.get('accounts'),
            only_no_api_key=not options.get('all', False),
            force=options.get('force', False),
        )
        self.stdout.write(self.style.SUCCESS(f'완료: {result}'))

        # 수집 후 자동 정정: 최신 엑셀에서 빠진(판매중지/이탈) 상품의 status_type을 바로잡음.
        # (upsert만 하면 빠진 상품이 stale '판매중'으로 남아 적자/ROAS 오판 → 즉시 정정)
        try:
            from apps.cpc.management.commands.reconcile_11st_product_status import reconcile
            r = reconcile(account_filter=options.get('accounts'),
                          log=lambda msg: self.stdout.write(msg))
            self.stdout.write(self.style.SUCCESS(f'판매상태 정정: {r["marked"]}건 판매중지'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'판매상태 정정 스킵(오류): {e}'))

        # 구매원가(예비상품 마켓가) 비정규화 컬럼 갱신 → /myproduct 구매원가/차이 정렬 최신화
        try:
            from apps.cpc.eleven_my_product_service import refresh_purchase_costs
            n = refresh_purchase_costs()
            self.stdout.write(self.style.SUCCESS(f'구매원가 갱신: {n}건'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'구매원가 갱신 스킵(오류): {e}'))
