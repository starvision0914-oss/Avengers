"""11번가 확인필요(역마진) 상품의 판매가를 예비상품 마켓가(purchase_cost)로 맞춤.
(2026-08-24) Selenium 상품수정 화면 자동화를 새로 만들 필요 없이, 이미 상품명 최적화
(optimize_11st_product_names.py)에서 검증된 hulk REST API(_get_session/_get_hulk_detail/
_put_hulk_update)를 그대로 재사용 — 로그인만 브라우저로 짧게 하고 이후는 순수 API 호출이라
Selenium으로 화면을 매번 조작하는 것보다 훨씬 빠르고 안정적이다.

사용법:
  python manage.py apply_11st_price_match --account jinag7460 --pct 20 [--dry-run] [--limit N]
  python manage.py apply_11st_price_match --all --pct 20   # 집중관리 전체 계정 순회
"""
import time
import random

import requests as _requests
from django.core.management.base import BaseCommand
from django.db.models import F

from apps.cpc.models import CrawlerAccount, ElevenMyProduct
from apps.cpc.management.commands.optimize_11st_product_names import (
    _get_session, _get_hulk_detail, _put_hulk_update,
)
from apps.cpc import eleven_block_guard as guard


class Command(BaseCommand):
    help = '11번가 확인필요(역마진) 상품 판매가를 예비상품 마켓가로 맞춤 (hulk API)'

    def add_arguments(self, parser):
        parser.add_argument('--account', type=str, help='특정 계정 login_id')
        parser.add_argument('--all', action='store_true', help='활성 전체 계정')
        parser.add_argument('--pct', type=int, default=20, help='마켓가 대비 몇 %% 이상 저가일 때 역마진으로 볼지(기본 20)')
        parser.add_argument('--limit', type=int, help='계정당 최대 처리건수(테스트용)')
        parser.add_argument('--dry-run', action='store_true', help='실제 변경 없이 대상만 출력')

    def handle(self, *args, **options):
        pct = min(max(options['pct'], 1), 99)
        mult = (100 - pct) / 100.0
        dry_run = options['dry_run']

        if options['account']:
            accounts = list(CrawlerAccount.objects.filter(platform='11st', login_id=options['account']))
        elif options['all']:
            accounts = list(CrawlerAccount.objects.filter(platform='11st', is_active=True))
        else:
            self.stdout.write(self.style.ERROR('--account 또는 --all 중 하나는 필요합니다'))
            return

        if not accounts:
            self.stdout.write('대상 계정 없음')
            return

        if not dry_run:
            ok, holder = guard.preflight('11st_price_match', platform='11st')
            if not ok:
                self.stdout.write(self.style.WARNING(f'⏭️ 건너뜀 — {holder}'))
                return

        total_ok = total_fail = total_skip = 0
        try:
            for acct in accounts:
                # L코드(도매마트)는 --pct 기준이 아니라 고정 50%(마켓가*0.5 이하일 때만) 인상 —
                # 2026-08-27 사용자 확정: "L코드는 역마진 확인필요 판매가의 50%이하일때만 가격을
                # 높이고 있다". W코드는 기존대로 --pct 기준.
                qs = (ElevenMyProduct.objects
                      .filter(account=acct, status_type='판매중', purchase_cost__gt=0)
                      .filter(
                          Q(seller_product_code__istartswith='LCE_', sale_price__lte=F('purchase_cost') * 0.5) |
                          (~Q(seller_product_code__istartswith='LCE_') & Q(sale_price__lte=F('purchase_cost') * mult))
                      )
                      .order_by('-id'))
                if options['limit']:
                    qs = qs[:options['limit']]
                products = list(qs)
                if not products:
                    self.stdout.write(f'[{acct.login_id}] 대상 없음')
                    continue

                self.stdout.write(f'[{acct.login_id}] 대상 {len(products)}건 (역마진 {pct}%+)')
                if dry_run:
                    for p in products[:20]:
                        self.stdout.write(f'  {p.product_no} {p.product_name[:30]} {p.sale_price}원 -> {p.purchase_cost}원')
                    continue

                try:
                    sess = _get_session(acct)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'[{acct.login_id}] 로그인 실패: {e}'))
                    total_fail += len(products)
                    continue

                for p in products:
                    try:
                        # 11번가는 판매가를 10원 단위로만 받음 — 마켓가(purchase_cost)에 5원
                        # 끝자리가 섞여있으면 400(판매가는 10원 단위로...) 거부됨(2026-08-27 실측,
                        # 전체 매칭상품의 11%가 10원단위 아님). 원가 이하로 내려가지 않도록 올림.
                        target_price = -(-p.purchase_cost // 10) * 10
                        detail = _get_hulk_detail(sess, p.product_no)
                        old_price = detail.get('sellPrice')
                        detail['sellPrice'] = target_price
                        try:
                            success = _put_hulk_update(sess, p.product_no, detail)
                        except _requests.exceptions.HTTPError as e:
                            # RAW_MATERIAL(원재료="상세설명 참조"인데 origin.code가 같이 남아있으면 400)
                            # — _apply_11st_decisions.py에서 검증된 반응형 대응과 동일 패턴(2026-08-27
                            # 실측: apply_11st_price_match 240건 실패 중 201건이 이 원인).
                            body = e.response.text if e.response is not None else ''
                            if 'RAW_MATERIAL' in body and detail.get('origin', {}).get('code'):
                                detail['origin']['code'] = None
                                success = _put_hulk_update(sess, p.product_no, detail)
                                self.stdout.write(f'  [{p.product_no}] (RAW_MATERIAL 대응 재시도)')
                            else:
                                raise
                        if success:
                            ElevenMyProduct.objects.filter(pk=p.pk).update(sale_price=target_price)
                            self.stdout.write(f'  [{p.product_no}] OK {old_price} -> {target_price}')
                            total_ok += 1
                        else:
                            self.stdout.write(f'  [{p.product_no}] 저장실패(status!=200)')
                            total_fail += 1
                    except Exception as e:
                        self.stdout.write(f'  [{p.product_no}] 오류: {e}')
                        total_fail += 1
                    time.sleep(1.2 + random.uniform(0, 0.5))
        finally:
            if not dry_run:
                guard.release_global_lock(platform='11st')

        self.stdout.write(self.style.SUCCESS(
            f'완료 — 성공 {total_ok} / 실패 {total_fail} / 스킵 {total_skip}'
            + (' (DRY-RUN)' if dry_run else '')))
