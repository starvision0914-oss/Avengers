from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '지마켓 적자상품 자동 판매중지·삭제 (기본 validate 검증, --real 실삭제)'

    def add_arguments(self, parser):
        parser.add_argument('--ym-from', default='2026-01')
        parser.add_argument('--ym-to', default='2026-06')
        parser.add_argument('--eid', help='특정 계정만')
        parser.add_argument('--limit', type=int, help='소량 테스트 개수')
        parser.add_argument('--real', action='store_true', help='실제 판매중지+삭제 (미지정=검증)')
        parser.add_argument('--stop-only', action='store_true', help='판매중지만(삭제 안 함)')
        parser.add_argument('--product-nos', nargs='*', dest='product_nos',
                            help='상품번호 지정 삭제(나의상품 선택삭제용). --eid 필수.')
        parser.add_argument('--targets-json', dest='targets_json', default=None,
                            help='다계정 일괄 지정(나의상품 선택). {"eid1":["pno",...], "eid2":[...]} JSON. '
                                 'run_delete가 계정별로 순차 처리 + 락 1회 획득(11번가 delete_loss_products와 동일 패턴).')
        parser.add_argument('--targets-file', dest='targets_file', default=None,
                            help='--targets-json과 동일 내용을 파일로 전달(대량일 때 OS 인자길이 한도 회피용).')

    def handle(self, *args, **o):
        from apps.cpc.views import _gmkt_product_rows
        from apps.cpc.models import protected_login_ids
        from crawlers.gmarket_loss_delete import run_delete

        class _Req:
            def __init__(self, p): self.query_params = p

        if o.get('targets_file') and not o.get('targets_json'):
            with open(o['targets_file'], 'r', encoding='utf-8') as f:
                o['targets_json'] = f.read()

        mode = 'stop_only' if o.get('stop_only') else ('real' if o['real'] else 'validate')
        protected = protected_login_ids('gmarket')

        # 다계정 지정상품(나의상품 선택 — 확인필요/고마진 등에서 여러 계정 상품 한 번에)
        if o.get('targets_json'):
            import json
            acc_map = json.loads(o['targets_json'])
            skipped_accs = [eid for eid in acc_map if eid in protected]
            targets = [{'login_id': eid, 'product_no': str(p), 'seller_code': '', 'status': ''}
                       for eid, pnos in acc_map.items() if eid not in protected for p in pnos]
            if skipped_accs:
                self.stdout.write(f'⛔ 테스트/타사 계정 제외: {", ".join(skipped_accs)}')
            self.stdout.write(f'다계정 지정상품 {len(targets)}개 / {len(acc_map) - len(skipped_accs)}계정 (mode={mode})')
            if not targets:
                self.stdout.write('대상 없음 — 종료')
                return
            res = run_delete(targets, mode=mode, log_fn=lambda m: self.stdout.write(m))
            self.stdout.write(str(res))
            return

        # 상품번호 지정 삭제(나의상품 선택삭제) — CLI 직접 호출 등 API뷰를 거치지 않는 경로 대비 이중 방어
        if o.get('product_nos'):
            eid = o.get('eid') or ''
            if eid in protected:
                self.stdout.write(f'⛔ {eid}는 테스트/타사 계정 — 조치 차단')
                return
            targets = [{'login_id': eid, 'product_no': str(p), 'seller_code': '', 'status': ''}
                       for p in o['product_nos']]
            self.stdout.write(f'지정상품 {len(targets)}개 (mode={mode}) eid={eid}')
            res = run_delete(targets, mode=mode, log_fn=lambda m: self.stdout.write(m))
            self.stdout.write(str(res))
            return

        params = {'ym_from': o['ym_from'], 'ym_to': o['ym_to'],
                  'cost_min': '2000', 'roas_max': '100', 'clicks_min': '10',
                  'eid': o.get('eid') or ''}
        rows = _gmkt_product_rows(_Req(params)).get('rows', [])
        # 테스트/타사 계정 상품은 '전체' 스윕에서도 항상 제외(뷰어·다운로드만 허용, 조치는 절대 금지)
        if protected:
            before = len(rows)
            rows = [r for r in rows if r.get('login_id') not in protected]
            if before - len(rows):
                self.stdout.write(f'테스트/타사 계정 제외: {before - len(rows)}개')
        # 판매중지(stop_only)는 광고전환ROAS만으로는 오탐(실제론 흑자인데 걸림)이 있을 수 있어,
        # 실매출 기준 ROAS(real_roas)가 150% 넘는(실제로는 괜찮은) 상품은 보호하고 제외한다.
        # 실매출 데이터가 없는 상품(real_roas=0)은 근거가 없으므로 그대로 대상에 포함.
        if mode == 'stop_only':
            before = len(rows)
            rows = [r for r in rows if (r.get('real_roas') or 0) <= 150]
            skipped = before - len(rows)
            if skipped:
                self.stdout.write(f'실매출ROAS>150% 제외(보호): {skipped}개')
        if o.get('limit'):
            rows = rows[:o['limit']]
        targets = [{'login_id': r['login_id'], 'product_no': r['product_no'],
                    'product_name': r.get('product_name', ''),
                    'seller_code': r.get('seller_code', ''), 'status': r.get('status', '')}
                   for r in rows if r.get('login_id') and r.get('product_no')]
        self.stdout.write(f'적자 대상 {len(targets)}개 (mode={mode})')
        for t in targets:
            self.stdout.write(f'  - [{t["login_id"]}] {t["product_no"]} {t.get("product_name") or "(상품명 미확인)"}')
        if not targets:
            self.stdout.write('대상 없음 — 종료')
            return
        res = run_delete(targets, mode=mode, log_fn=lambda m: self.stdout.write(m))
        self.stdout.write(str(res))
