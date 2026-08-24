"""지마켓 고단가(판매가가 예비상품 마켓가 대비 pct%+ 초과) 상품의 판매가를 마켓가(100%)로 인하.
apply_gmarket_price_match와 반대 방향(역마진=너무 쌈 / 고단가=너무 비쌈), 동일한 API 직접호출 재사용.

사용법:
  python manage.py apply_gmarket_price_cap --account rejoice234 --pct 100 [--dry-run] [--limit N]
  python manage.py apply_gmarket_price_cap --all --pct 100   # 활성 전체 계정
"""
from django.core.management.base import BaseCommand
from django.db.models import F

from apps.cpc.models import CrawlerAccount, GmarketMyProduct


class Command(BaseCommand):
    help = '지마켓 고단가 상품 판매가를 예비상품 마켓가로 인하 (API)'

    def add_arguments(self, parser):
        parser.add_argument('--account', type=str, help='특정 계정 login_id')
        parser.add_argument('--all', action='store_true', help='활성 전체 계정')
        parser.add_argument('--pct', type=int, default=100, help='마켓가 대비 몇 %% 초과일 때 고단가로 볼지(기본 100=2배)')
        parser.add_argument('--limit', type=int, help='계정당 최대 처리건수(테스트용)')
        parser.add_argument('--dry-run', action='store_true', help='실제 변경 없이 대상만 출력')

    def handle(self, *args, **options):
        from crawlers.gmarket_price_match import run_price_match

        pct = max(options['pct'], 1)
        mult = 1 + pct / 100.0
        dry_run = options['dry_run']

        if options['account']:
            accounts = list(CrawlerAccount.objects.filter(platform='gmarket', login_id=options['account']))
        elif options['all']:
            accounts = list(CrawlerAccount.objects.filter(platform='gmarket', is_active=True))
        else:
            self.stdout.write(self.style.ERROR('--account 또는 --all 중 하나는 필요합니다'))
            return

        if not accounts:
            self.stdout.write('대상 계정 없음')
            return

        targets = []
        for acct in accounts:
            qs = (GmarketMyProduct.objects
                  .filter(account=acct, status_type='판매중', purchase_cost__gt=0,
                          sale_price__gt=F('purchase_cost') * mult)
                  .order_by('-id'))
            if options['limit']:
                qs = qs[:options['limit']]
            products = list(qs)
            if not products:
                self.stdout.write(f'[{acct.login_id}] 대상 없음')
                continue
            self.stdout.write(f'[{acct.login_id}] 대상 {len(products)}건 (고단가 {pct}%+)')
            for p in products:
                if dry_run:
                    self.stdout.write(f'  {p.product_no} {(p.product_name or "")[:30]} {p.sale_price}원 -> {p.purchase_cost}원')
                else:
                    targets.append({'login_id': acct.login_id, 'product_no': p.product_no,
                                     'target_price': p.purchase_cost})

        if dry_run:
            self.stdout.write(self.style.SUCCESS('DRY-RUN — 위 목록 참고'))
            return

        if not targets:
            self.stdout.write('대상 없음 — 종료')
            return

        res = run_price_match(targets, log_fn=lambda m: self.stdout.write(m))
        self.stdout.write(str(res))
        if res.get('ok'):
            self.stdout.write(self.style.SUCCESS(
                f'완료 — 계정 {res["accounts"]} / 가격변경 {res["updated"]}건'))
