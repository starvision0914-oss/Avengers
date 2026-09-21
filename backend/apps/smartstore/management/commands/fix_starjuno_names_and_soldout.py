"""스타주노(starvis9942@gmail.com) 전용 1회성 정리 작업 (2026-09-21 사용자 요청):
  1) 판매자코드(W코드) 기준 오너클랜 원본 상품명과 다른 상품명을 오너클랜 원본으로 되돌림
     (apply_ss_products류 스크립트가 카테고리 키워드를 덧붙이며 "100매"처럼 수량이 실제와
     다르게 부풀려진 오류가 발견돼, 이 계정만 원본으로 복원 — 사용자 명시적 지시).
  2) OUTOFSTOCK(품절) 상태 상품을 SUSPENSION(판매중지)으로 전환.
두 작업 모두 네이버 커머스 API로 실제 반영 + 로컬 DB 동기화. 진행상황은 표준출력(로그파일 리다이렉트)로.
"""
import re
import time
from django.core.management.base import BaseCommand
from django.db import close_old_connections


class Command(BaseCommand):
    help = '스타주노 상품명 오너클랜 원본 복원 + 품절상품 판매중지'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='API 호출 없이 대상만 집계')
        parser.add_argument('--skip-names', action='store_true', help='상품명 복원 단계 생략')
        parser.add_argument('--skip-soldout', action='store_true', help='품절 판매중지 단계 생략')
        parser.add_argument('--delay', type=float, default=0.45)

    def handle(self, *args, **o):
        from apps.smartstore.models import SmartStoreAccount, SmartStoreProduct
        from apps.ownerclan.models import OwnerclanProduct
        from apps.smartstore.services.naver_api import (
            _get_access_token, update_product_name_api, suspend_product_api,
        )

        LOGIN = 'starvis9942@gmail.com'
        DELAY = o['delay']
        dry = o['dry_run']

        acc = SmartStoreAccount.objects.get(login_id=LOGIN)
        token = None if dry else _get_access_token(acc.commerce_api_key, acc.commerce_secret_key)

        # ── 1) 상품명 복원 ──
        if not o['skip_names']:
            self.stdout.write('=== 1단계: 상품명 오너클랜 원본 복원 ===')
            oc_map = dict(OwnerclanProduct.objects.exclude(product_name='').values_list('seller_code1', 'product_name'))
            self.stdout.write(f'오너클랜 코드 {len(oc_map)}건 로드')

            qs = list(SmartStoreProduct.objects.filter(account=acc).exclude(seller_management_code='')
                      .values('id', 'name', 'seller_management_code', 'channel_product_no'))
            targets = []
            for p in qs:
                code = re.sub(r'^(WDM_|AUTO_)', '', p['seller_management_code'] or '')
                oc_name = oc_map.get(code)
                if not oc_name or p['name'].strip() == oc_name.strip():
                    continue
                targets.append((p, oc_name))
            self.stdout.write(f'상품명 복원 대상: {len(targets)}건')

            ok, fail = 0, 0
            for i, (p, oc_name) in enumerate(targets, 1):
                if dry:
                    ok += 1
                    continue
                cpn = p['channel_product_no']
                if not cpn:
                    fail += 1
                    self.stdout.write(f'[{i}/{len(targets)}] id={p["id"]} channel_product_no 없음 — 스킵')
                    continue
                try:
                    update_product_name_api(cpn, oc_name, token)
                    SmartStoreProduct.objects.filter(id=p['id']).update(name=oc_name)
                    ok += 1
                except Exception as e:
                    fail += 1
                    self.stdout.write(f'[{i}/{len(targets)}] id={p["id"]} 실패: {str(e)[:150]}')
                if i % 50 == 0:
                    self.stdout.write(f'  진행 {i}/{len(targets)} (성공 {ok} / 실패 {fail})')
                    close_old_connections()
                time.sleep(DELAY)
            self.stdout.write(f'상품명 복원 완료: 성공 {ok} / 실패 {fail}')

        # ── 2) 품절 → 판매중지 ──
        if not o['skip_soldout']:
            self.stdout.write('=== 2단계: 품절(OUTOFSTOCK) → 판매중지(SUSPENSION) ===')
            qs2 = list(SmartStoreProduct.objects.filter(account=acc, status_type='OUTOFSTOCK')
                       .values('id', 'name', 'channel_product_no'))
            self.stdout.write(f'품절 판매중지 대상: {len(qs2)}건')

            ok2, fail2 = 0, 0
            for i, p in enumerate(qs2, 1):
                if dry:
                    ok2 += 1
                    continue
                cpn = p['channel_product_no']
                if not cpn:
                    fail2 += 1
                    self.stdout.write(f'[{i}/{len(qs2)}] id={p["id"]} channel_product_no 없음 — 스킵')
                    continue
                try:
                    suspend_product_api(cpn, token)
                    SmartStoreProduct.objects.filter(id=p['id']).update(status_type='SUSPENSION')
                    ok2 += 1
                except Exception as e:
                    fail2 += 1
                    self.stdout.write(f'[{i}/{len(qs2)}] id={p["id"]} 실패: {str(e)[:150]}')
                if i % 50 == 0:
                    self.stdout.write(f'  진행 {i}/{len(qs2)} (성공 {ok2} / 실패 {fail2})')
                    close_old_connections()
                time.sleep(DELAY)
            self.stdout.write(f'품절 판매중지 완료: 성공 {ok2} / 실패 {fail2}')

        self.stdout.write('=== 전체 종료 ===')
