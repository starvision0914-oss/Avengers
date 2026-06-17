"""적자상품 자동 판매중지·삭제 실행 (셀러오피스).
적자 목록을 산출 → eleven_loss_delete.run_delete 호출.
안전: 기본 dry-run. 실삭제는 --real + 셀러오피스 플로우 검증 후."""
from datetime import date, datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = '적자상품 자동 판매중지·삭제'

    def add_arguments(self, parser):
        parser.add_argument('--from', dest='date_from', default='2026-01-01')
        parser.add_argument('--to', dest='date_to', default=None)
        parser.add_argument('--roas-max', type=float, default=100)
        parser.add_argument('--cost-min', type=float, default=2000)
        parser.add_argument('--clicks-min', type=float, default=10)
        parser.add_argument('--mode', choices=['validate', 'real'], default='validate',
                            help="validate(기본, 파괴적 클릭 없음) | real(실삭제)")
        parser.add_argument('--real', action='store_true', help='--mode real 과 동일')
        parser.add_argument('--eid', default=None, help='특정 계정만 처리(테스트용)')
        parser.add_argument('--product-nos', nargs='*', dest='product_nos',
                            help='상품번호 지정 삭제(나의상품 선택삭제용). --eid 필수.')

    def handle(self, *args, **o):
        from apps.cpc.views import _eleven_product_rows, _active_eids
        from crawlers.eleven_loss_delete import run_delete
        mode = 'real' if o['real'] else o['mode']
        # 상품번호 지정 삭제(나의상품 선택삭제) — 적자 산출 없이 그 상품만. run_delete가 status 무관 처리.
        if o.get('product_nos'):
            eid = o['eid'] or ''
            targets = [{'eleven_id': eid, 'product_no': str(p), 'seller_code': '', 'status': ''}
                       for p in o['product_nos']]
            self.stdout.write(f'지정상품 {len(targets)}개 / mode={mode} / eid={eid}')
            res = run_delete(targets, mode=mode, eid_filter=eid or None, log_fn=lambda m: self.stdout.write(m))
            self.stdout.write(str({k: res.get(k) for k in ('mode', 'accounts', 'rest_done', 'marked', 'failed', 'skipped')}))
            return
        d0 = datetime.strptime(o['date_from'], '%Y-%m-%d').date()
        d1 = datetime.strptime(o['date_to'], '%Y-%m-%d').date() if o['date_to'] else (timezone.localdate() - timedelta(days=1))
        eids = [o['eid']] if o['eid'] else _active_eids()
        allrows = []
        for e in eids:
            allrows += _eleven_product_rows(e, d0, d1, None, o['roas_max'], o['cost_min'], o['clicks_min'])
        # 판매금지/판매중/판매중지/품절을 그대로 넘김(run_delete가 1·2단계로 분리 처리). status 동반 필수.
        targets = [{'eleven_id': r['eleven_id'], 'product_no': r['product_no'],
                    'seller_code': r['seller_code'], 'status': r.get('status')}
                   for r in allrows]
        self.stdout.write(f'적자 {len(targets)}개 / mode={mode} / eid={o["eid"] or "전체"}')
        res = run_delete(targets, mode=mode, eid_filter=o['eid'],
                         log_fn=lambda m: self.stdout.write(m))
        self.stdout.write(str({k: res.get(k) for k in ('mode', 'accounts', 'banned_done', 'rest_done', 'marked', 'failed', 'skipped')}))
