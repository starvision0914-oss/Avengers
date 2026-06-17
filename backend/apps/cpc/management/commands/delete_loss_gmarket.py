from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '지마켓 적자상품 자동 판매중지·삭제 (기본 validate 검증, --real 실삭제)'

    def add_arguments(self, parser):
        parser.add_argument('--ym-from', default='2026-01')
        parser.add_argument('--ym-to', default='2026-06')
        parser.add_argument('--eid', help='특정 계정만')
        parser.add_argument('--limit', type=int, help='소량 테스트 개수')
        parser.add_argument('--real', action='store_true', help='실제 판매중지+삭제 (미지정=검증)')
        parser.add_argument('--product-nos', nargs='*', dest='product_nos',
                            help='상품번호 지정 삭제(나의상품 선택삭제용). --eid 필수.')

    def handle(self, *args, **o):
        from apps.cpc.views import _gmkt_product_rows
        from crawlers.gmarket_loss_delete import run_delete

        class _Req:
            def __init__(self, p): self.query_params = p

        # 상품번호 지정 삭제(나의상품 선택삭제)
        if o.get('product_nos'):
            eid = o.get('eid') or ''
            targets = [{'login_id': eid, 'product_no': str(p), 'seller_code': '', 'status': ''}
                       for p in o['product_nos']]
            self.stdout.write(f'지정상품 {len(targets)}개 (mode={"real" if o["real"] else "validate"}) eid={eid}')
            res = run_delete(targets, mode=('real' if o['real'] else 'validate'),
                             log_fn=lambda m: self.stdout.write(m))
            self.stdout.write(str(res))
            return

        params = {'ym_from': o['ym_from'], 'ym_to': o['ym_to'],
                  'cost_min': '2000', 'roas_max': '100', 'clicks_min': '10',
                  'eid': o.get('eid') or ''}
        rows = _gmkt_product_rows(_Req(params)).get('rows', [])
        if o.get('limit'):
            rows = rows[:o['limit']]
        targets = [{'login_id': r['login_id'], 'product_no': r['product_no'],
                    'seller_code': r.get('seller_code', ''), 'status': r.get('status', '')}
                   for r in rows if r.get('login_id') and r.get('product_no')]
        self.stdout.write(f'적자 대상 {len(targets)}개 (mode={"real" if o["real"] else "validate"})')
        if not targets:
            self.stdout.write('대상 없음 — 종료')
            return
        res = run_delete(targets, mode=('real' if o['real'] else 'validate'),
                         log_fn=lambda m: self.stdout.write(m))
        self.stdout.write(str(res))
