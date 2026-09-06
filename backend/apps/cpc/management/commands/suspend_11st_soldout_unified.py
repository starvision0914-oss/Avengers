"""11번가 '판매중' 상품 전체를 판매자코드 유형별(W코드/L코드/도매매코드)로 나눠 각 소싱처의
실제 상태를 확인하고, 품절·단종·존재안함(미확인)으로 확인된 상품을 판매중지로 전환하는 통합 커맨드.

- W코드(오너클랜): OwnerclanLiveStatus 캐시(주5일 순환점검) 기준. 아직 점검 안 된 코드는 대상 아님.
- L코드(도매마트): LCodeStatus 캐시(실시간 조회 진행중) 기준. 아직 점검 안 된 코드는 대상 아님.
- 도매매코드(순수 숫자 7자리): 캐시가 없어 실행 시점에 도매매 Open API로 즉시 라이브 조회
  (건당 --sleep초 페이싱, sync_11st_domeggook_stock.py와 동일 방식).

실행은 crawlers.eleven_suspend_only.verify_and_suspend_by_status로 처리한다 — 계정별로 먼저
실시간 판매상태를 재조회해 판매중/품절 순수배치로 나눈 뒤 처리하므로, DB상 상태와 11번가 실제
상태가 어긋나 배치가 섞여도(재시도 등으로 이미 반영된 경우 등) 11번가의 '섞인 배치 전체거부'를
피할 수 있다([[project_11st_jinag7460_suspend_reject]]).

사용법:
  python manage.py suspend_11st_soldout_unified --dry-run
  python manage.py suspend_11st_soldout_unified --real
  python manage.py suspend_11st_soldout_unified --real --account tmxkzhfldk9
"""
import re
import time

from django.core.management.base import BaseCommand

DOME_CODE_RE = re.compile(r'^[0-9]{7}$')


class Command(BaseCommand):
    help = "11번가 판매중 상품 W코드/L코드/도매매코드 통합 실제상태 검증 + 확인된 품절·미확인 판매중지"

    def add_arguments(self, parser):
        parser.add_argument('--account', help='특정 11번가 login_id만')
        parser.add_argument('--accounts', help='여러 login_id, 콤마구분(예: a,b,c)')
        parser.add_argument('--focused', action='store_true',
                             help='집중관리 계정(CrawlerAccount.is_focused=True, 11st)만 대상')
        parser.add_argument('--dry-run', action='store_true', help='실제 판매중지 없이 대상 목록/건수만 출력')
        parser.add_argument('--real', action='store_true', help='실제 판매중지 실행')
        parser.add_argument('--api-key', default='eadf63ce569e62d451d744f42c328d17',
                             help='도매매 Open API 키(기본: 스피드고 전송기 키)')
        parser.add_argument('--sleep', type=float, default=0.4, help='도매매 API 호출 간 대기(초), 429 방지')

    def handle(self, *args, **opts):
        from apps.cpc.models import ElevenMyProduct, CrawlerAccount, protected_login_ids
        from apps.cpc.eleven_my_product_service import get_lcode_soldout_rows, get_ownerclan_wcode_soldout_rows
        from apps.cpc.management.commands.sync_11st_domeggook_stock import _fetch_item

        dry_run = not opts['real']
        protected = protected_login_ids('11st')

        acct_set = None
        if opts.get('account'):
            acct_set = {opts['account']}
        elif opts.get('accounts'):
            acct_set = {a.strip() for a in opts['accounts'].split(',') if a.strip()}
        elif opts.get('focused'):
            acct_set = set(CrawlerAccount.objects.filter(platform='11st', is_focused=True)
                            .values_list('login_id', flat=True))
            self.stdout.write(f'집중관리 계정 {len(acct_set)}개 대상')

        def _filt(rows):
            return [(l, p) for l, p in rows
                    if l not in protected and (acct_set is None or l in acct_set)]

        self.stdout.write('=== 1/3 W코드(오너클랜) 확인 ===')
        w_rows = _filt(get_ownerclan_wcode_soldout_rows(
            ElevenMyProduct, 'seller_product_code', 'product_no', 'status_type', '판매중'))
        self.stdout.write(f'W코드 확인된 품절/단종/미확인: {len(w_rows)}건')

        self.stdout.write('=== 2/3 L코드(도매마트) 확인 ===')
        l_rows = _filt(get_lcode_soldout_rows(
            ElevenMyProduct, 'seller_product_code', 'product_no', 'status_type', '판매중'))
        self.stdout.write(f'L코드 확인된 품절/미확인: {len(l_rows)}건')

        self.stdout.write('=== 3/3 도매매코드 라이브조회(API) ===')
        dome_qs = (ElevenMyProduct.objects.filter(status_type='판매중')
                   .exclude(account__login_id__in=protected).select_related('account'))
        if acct_set is not None:
            dome_qs = dome_qs.filter(account__login_id__in=acct_set)
        dome_products = [p for p in dome_qs if DOME_CODE_RE.match(p.seller_product_code or '')]
        self.stdout.write(f'도매매코드 판매중 상품 조회 대상: {len(dome_products)}건')

        dome_rows = []
        aid = opts['api_key']
        for i, p in enumerate(dome_products):
            status = _fetch_item(aid, p.seller_product_code)
            if status != '판매중':
                dome_rows.append((p.account.login_id, p.product_no))
            if (i + 1) % 50 == 0:
                self.stdout.write(f'  도매매 진행 {i + 1}/{len(dome_products)} (대상누적 {len(dome_rows)})')
            time.sleep(opts['sleep'])
        self.stdout.write(f'도매매코드 확인된 품절/미확인: {len(dome_rows)}건')

        all_rows = w_rows + l_rows + dome_rows
        self.stdout.write('')
        self.stdout.write(f'=== 합계: W {len(w_rows)} + L {len(l_rows)} + 도매매 {len(dome_rows)} '
                           f'= 총 {len(all_rows)}건 판매중지 대상 ===')

        if not all_rows:
            self.stdout.write('대상 없음, 종료')
            return

        if dry_run:
            self.stdout.write('[dry-run] 실제 반영 없음. 샘플 30건:')
            for l, p in all_rows[:30]:
                self.stdout.write(f'  {l} {p}')
            return

        from crawlers.eleven_suspend_only import verify_and_suspend_by_status
        targets = [{'login_id': l, 'product_no': p} for l, p in all_rows]
        result = verify_and_suspend_by_status(targets, log_fn=lambda m: self.stdout.write(m))
        self.stdout.write(self.style.SUCCESS(f'=== 완료: {result} ==='))
