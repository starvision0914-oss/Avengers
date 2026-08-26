"""지마켓/옥션(ESM) 나의 상품 수집 — GmarketMyProduct에 누적 저장(상품번호 기준 중복제거)."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '지마켓/옥션 ESM 나의 상품 수집 (엑셀 다운로드 파싱)'

    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*', help='특정 계정만 수집')

    def handle(self, *args, **options):
        from crawlers.gmarket_product_crawler import run_all_accounts
        result = run_all_accounts(
            log_fn=lambda msg: self.stdout.write(msg),
            account_filter=options.get('accounts'),
        )
        self.stdout.write(self.style.SUCCESS(f'완료: {result}'))

        # 구매원가(예비상품 마켓가 / L코드 도매가×1.5) 비정규화 컬럼 갱신 → 확인필요(역마진) 최신화
        try:
            from apps.cpc.eleven_my_product_service import refresh_gmarket_purchase_costs
            n = refresh_gmarket_purchase_costs()
            self.stdout.write(self.style.SUCCESS(f'구매원가 갱신: {n}건'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'구매원가 갱신 스킵(오류): {e}'))
