from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '롯데온 죽은 W코드 상품 정리 (기본 validate 검증, --delete 실제 삭제(비가역), --real 판매종료(레거시, 비가역))'

    def add_arguments(self, parser):
        parser.add_argument('--delete', action='store_true', help='실제 삭제(완전 비가역, 재판매 불가). 미지정=검증')
        parser.add_argument('--real', action='store_true', help='(레거시) 실제 판매종료(비가역). --delete 미지정시만 유효')
        parser.add_argument('--targets-json', dest='targets_json', default=None,
                             help='{"login_id1":["seller_product_code",...], ...} JSON')
        parser.add_argument('--targets-file', dest='targets_file', default=None,
                             help='--targets-json과 동일 내용을 파일로 전달(대량 인자길이 한도 회피용).')

    def handle(self, *args, **o):
        import json
        from crawlers.lotteon_loss_delete import run_delete

        if o.get('targets_file') and not o.get('targets_json'):
            with open(o['targets_file'], 'r', encoding='utf-8') as f:
                o['targets_json'] = f.read()

        if not o.get('targets_json'):
            self.stdout.write('대상 없음(targets-json/targets-file 미지정) — 종료')
            return

        acc_map = json.loads(o['targets_json'])
        targets = [{'login_id': eid, 'product_no': str(p)}
                   for eid, codes in acc_map.items() for p in codes]
        mode = 'delete' if o.get('delete') else ('real' if o.get('real') else 'validate')
        self.stdout.write(f'대상 {len(targets)}개 / {len(acc_map)}계정 (mode={mode})')
        if not targets:
            self.stdout.write('대상 없음 — 종료')
            return
        res = run_delete(targets, mode=mode, log_fn=lambda m: self.stdout.write(m))
        self.stdout.write(str(res))
