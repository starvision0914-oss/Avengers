"""쿠팡 등록상품 전체 판매중지 (Wing Open API). 11번가/지마켓과 동일한 --targets-file 방식.
예) python manage.py coupang_suspend_products --targets-file targets.json
    targets.json: {"login_id": ["sellerProductId", ...], ...}"""
import json

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '쿠팡 등록상품 전체 판매중지'

    def add_arguments(self, parser):
        parser.add_argument('--targets-file', dest='targets_file', required=True,
                             help='{"login_id": ["sellerProductId", ...], ...} 형식 JSON 파일')

    def handle(self, *args, **o):
        import requests
        from apps.coupang.models import CoupangAccount
        from apps.coupang.services import stop_product_sale

        with open(o['targets_file'], 'r', encoding='utf-8') as f:
            targets = json.load(f)

        total = sum(len(v) for v in targets.values())
        self.stdout.write(f'쿠팡 판매중지 대상(등록상품) {total}개 / {len(targets)}계정')

        success = failed = 0
        for login_id, ids in targets.items():
            try:
                acc = CoupangAccount.objects.get(login_id=login_id)
            except CoupangAccount.DoesNotExist:
                self.stdout.write(f'[{login_id}] 계정 없음 — 스킵 {len(ids)}건')
                failed += len(ids)
                continue
            if not acc.has_api_key:
                self.stdout.write(f'[{login_id}] 오픈API 키 미등록 — 스킵 {len(ids)}건')
                failed += len(ids)
                continue
            for pid in ids:
                try:
                    ok, fail = stop_product_sale(acc, pid, log_fn=self.stdout.write)
                    self.stdout.write(f'  [{login_id}] {pid} 옵션 {ok}개 판매중지 성공, {fail}개 실패')
                    if ok and not fail:
                        success += 1
                    else:
                        failed += 1
                except requests.HTTPError as e:
                    body = e.response.text[:200] if e.response is not None else str(e)
                    self.stdout.write(f'  [{login_id}] {pid} 판매중지 실패: {body}')
                    failed += 1
                except Exception as e:
                    self.stdout.write(f'  [{login_id}] {pid} 오류: {str(e)[:150]}')
                    failed += 1

        self.stdout.write(f'완료 — 성공 {success} / 실패 {failed}')
