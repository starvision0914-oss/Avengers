"""11번가 상품 중 판매자관리코드가 도매매코드(7자리 순수숫자, [[reference_domeggook_code_format]])인
상품을 도매매 Open API(getItemView)로 조회해, 소싱처에서 이미 판매종료/삭제된 상품을
11번가에서 판매중지로 전환한다. 오너클랜용 suspend_11st_confirmed_soldout.py와 같은 개념이지만
소스가 도매매 API라는 점만 다르다.

2026-09-05/06 실측: 239건 중 판매중 148 / 판매종료 4 / 상품삭제 80 / 요청제한(재시도로 해소) —
판매종료+삭제 총 84건을 실제 판매중지 처리해 정상 완료함(0 실패).

API 키: mobile.domeggook.com/APIs/gate 에서 발급된 기존 키("스피드고 전송기") 재사용.
요청 과다 시 429(Too Many Requests) 발생 — 건당 0.3~0.5초 간격 권장, 실패분은 재시도.

사용법:
  python manage.py sync_11st_domeggook_stock --dry-run
  python manage.py sync_11st_domeggook_stock
  python manage.py sync_11st_domeggook_stock --account tmxk24
"""
import json
import re
import time
import urllib.request

from django.core.management.base import BaseCommand

API_URL = 'https://www.domeggook.com/ssl/api/'
DOME_CODE_RE = re.compile(r'^[0-9]{7}$')


def _fetch_item(aid, no):
    """도매매 getItemView 1건 조회. 성공 시 (status, inventory) 반환, 실패/미존재 시 None."""
    url = (f'{API_URL}?ver=4.6&mode=getItemView&aid={aid}&om=json&no={no}')
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                data = json.load(r)
            if 'errors' in data:
                return None  # 존재하지 않음/기타 오류 = 소싱처에 없음
            basis = data.get('domeggook', {}).get('basis', {})
            return basis.get('status')
        except Exception as e:
            if '429' in str(e) and attempt < 2:
                time.sleep(2)
                continue
            return 'RETRY_FAILED' if attempt == 2 else None
    return None


class Command(BaseCommand):
    help = "11번가 도매매코드 상품을 도매매 실재고/판매상태 기준으로 확인해 종료/삭제분 판매중지 전환"

    def add_arguments(self, parser):
        parser.add_argument('--account', help='특정 11번가 login_id만')
        parser.add_argument('--api-key', default='eadf63ce569e62d451d744f42c328d17',
                             help='도매매 Open API 키(기본: 스피드고 전송기 키)')
        parser.add_argument('--dry-run', action='store_true', help='실제 판매중지 없이 대상만 출력')
        parser.add_argument('--sleep', type=float, default=0.4, help='API 호출 간 대기(초), 429 방지')

    def handle(self, *args, **opts):
        from apps.cpc.models import ElevenMyProduct, protected_login_ids

        dry_run = opts['dry_run']
        aid = opts['api_key']

        protected = protected_login_ids('11st')
        qs = ElevenMyProduct.objects.filter(
            status_type='판매중'
        ).exclude(account__login_id__in=protected).select_related('account')
        if opts['account']:
            qs = qs.filter(account__login_id=opts['account'])

        products = [p for p in qs if DOME_CODE_RE.match(p.seller_product_code or '')]
        self.stdout.write(f'도매매코드 판매중 상품: {len(products)}건')

        to_suspend = []
        retry_needed = []
        ended = 0
        gone = 0

        for i, p in enumerate(products):
            status = _fetch_item(aid, p.seller_product_code)
            if status == 'RETRY_FAILED':
                retry_needed.append(p)
            elif status is None:
                gone += 1
                to_suspend.append({'login_id': p.account.login_id, 'product_no': p.product_no})
            elif status != '판매중':
                ended += 1
                to_suspend.append({'login_id': p.account.login_id, 'product_no': p.product_no})
            if (i + 1) % 50 == 0:
                self.stdout.write(f'  진행 {i + 1}/{len(products)} (대상누적 {len(to_suspend)})')
            time.sleep(opts['sleep'])

        self.stdout.write(
            f'조회 완료 — 판매종료 {ended} / 상품삭제(미존재) {gone} / '
            f'요청제한재시도필요 {len(retry_needed)} / 판매중지대상 {len(to_suspend)}'
        )

        if dry_run:
            for t in to_suspend[:50]:
                self.stdout.write(f'[dry-run] {t["login_id"]} {t["product_no"]} → 판매중지 예정')
            self.stdout.write('(dry-run — 실제 반영 없음)')
            return

        if not to_suspend:
            self.stdout.write('대상 없음, 종료')
            return

        from crawlers.eleven_suspend_only import suspend_only
        result = suspend_only(to_suspend, mode='real', log_fn=lambda m: self.stdout.write(m))
        self.stdout.write(self.style.SUCCESS(f'=== 완료: {result} ==='))

        fully_done_accounts = {
            r['eleven_id'] for r in result.get('results', [])
            if r.get('applied', 0) == r.get('requested', 0) and r.get('failed_batches', 0) == 0
        }
        product_nos = [t['product_no'] for t in to_suspend if t['login_id'] in fully_done_accounts]
        updated = ElevenMyProduct.objects.filter(
            product_no__in=product_nos, status_type='판매중'
        ).update(status_type='판매중지') if product_nos else 0
        self.stdout.write(f'DB 동기화: 완전성공계정 {len(fully_done_accounts)}개 / {updated}건 판매중지로 반영')
