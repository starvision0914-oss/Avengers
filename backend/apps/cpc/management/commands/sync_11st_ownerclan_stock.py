"""11번가 '품절' 상품의 실제 판매상태를 오너클랜 실재고 기준으로 정정(스마트스토어
sync_ownerclan_stock과 동일 개념). hulk API(optimize_11st_product_names.py에서 검증된
_get_session/_get_hulk_detail/_put_hulk_update)로 stockQuantity를 갱신하면 11번가가
자동으로 판매상태(품절/판매중)를 재계산한다.

범위: 이번 1차는 옵션 없는 단일상품만 처리(옵션상품은 sellerStockCode 매칭이 불완전해
잘못 반영할 위험이 있어 스킵하고 로그만 남김 — 필요시 2차로 확장).

사용법:
  python manage.py sync_11st_ownerclan_stock --account tmxkqhrhksth000 --dry-run
  python manage.py sync_11st_ownerclan_stock --account tmxkqhrhksth000
  python manage.py sync_11st_ownerclan_stock  (전체 계정)
"""
import time

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "11번가 품절상품을 오너클랜 실재고 기준으로 정정(옵션없는 단일상품만, 1차)"

    def add_arguments(self, parser):
        parser.add_argument('--account', help='특정 11번가 login_id만')
        parser.add_argument('--oc-account', default='rejoice999', help='사용할 오너클랜 API 계정 login_id')
        parser.add_argument('--limit', type=int, default=0, help='0=전체(계정 단위 제한 아님, 상품 단위)')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--chunk', type=int, default=50)

    def handle(self, *args, **opts):
        import requests
        from apps.cpc.models import CrawlerAccount, ElevenMyProduct
        from apps.cpc.management.commands.optimize_11st_product_names import (
            _get_session, _get_hulk_detail, _put_hulk_update,
        )
        from apps.ownerclan.models import OwnerclanApiAccount
        from crawlers.ownerclan_api_crawler import _get_token, API_URL
        from crawlers.browser import stop_display

        dry_run = opts['dry_run']
        chunk_size = opts['chunk']

        oc_acc = OwnerclanApiAccount.objects.filter(login_id=opts['oc_account'], is_active=True).first()
        if not oc_acc:
            self.stderr.write(f'오너클랜 API 계정 없음: {opts["oc_account"]}')
            return
        oc_token = _get_token(oc_acc)
        oc_headers = {'Authorization': f'Bearer {oc_token}'}

        qs = ElevenMyProduct.objects.filter(status_type='품절', seller_product_code__regex=r'^W[0-9A-Fa-f]+$')
        if opts['account']:
            qs = qs.filter(account__login_id=opts['account'])
        qs = qs.select_related('account').order_by('account_id', 'id')
        if opts['limit']:
            qs = qs[:opts['limit']]

        products = list(qs)
        by_account = {}
        for p in products:
            by_account.setdefault(p.account_id, {'account': p.account, 'items': []})['items'].append(p)

        self.stdout.write(f'대상: {len(products)}건 / {len(by_account)}계정')

        def oc_lookup(codes):
            keys_str = ', '.join(f'"{c}"' for c in codes)
            query = f'query {{ itemsByKeys(keys: [{keys_str}]) {{ key status options {{ key quantity status }} }} }}'
            for attempt in range(3):
                try:
                    r = requests.get(API_URL, params={'query': query}, headers=oc_headers, timeout=45)
                    r.raise_for_status()
                    return {it['key']: it for it in (r.json().get('data', {}).get('itemsByKeys') or []) if it}
                except Exception:
                    if attempt == 2:
                        return None
                    time.sleep(3)

        fixed = 0
        unchanged = 0
        skipped_option = 0
        no_match = 0
        errors = 0

        for acc_id, group in by_account.items():
            acc = group['account']
            items = group['items']
            try:
                sess = _get_session(acc)
            except Exception as e:
                self.stderr.write(f'[{acc.login_id}] 로그인 실패: {e}')
                errors += len(items)
                continue

            try:
                for i in range(0, len(items), chunk_size):
                    batch = items[i:i + chunk_size]
                    codes = [p.seller_product_code for p in batch]
                    oc_map = oc_lookup(codes)
                    if oc_map is None:
                        self.stderr.write(f'[{acc.login_id}] 오너클랜 조회 실패, 배치 스킵')
                        errors += len(batch)
                        continue

                    for p in batch:
                        oc_item = oc_map.get(p.seller_product_code)
                        if not oc_item:
                            no_match += 1
                            continue
                        if oc_item.get('status') != 'available':
                            unchanged += 1
                            continue
                        try:
                            detail = _get_hulk_detail(sess, p.product_no)
                        except Exception as e:
                            errors += 1
                            self.stderr.write(f'[{acc.login_id}] {p.product_no} 조회실패: {e}')
                            continue

                        opt = detail.get('option') or {}
                        has_options = bool((opt.get('combination') or {}).get('items'))
                        if has_options:
                            skipped_option += 1
                            continue

                        best_qty = max((o.get('quantity') or 0) for o in (oc_item.get('options') or [{'quantity': 0}]))
                        new_qty = min(best_qty, 999) or 999

                        if dry_run:
                            fixed += 1
                            self.stdout.write(f'[dry-run] {acc.login_id} {p.seller_product_code} {p.product_name[:30]} stock 0→{new_qty}')
                            continue

                        detail['stockQuantity'] = new_qty
                        try:
                            ok = _put_hulk_update(sess, p.product_no, detail)
                        except requests.exceptions.HTTPError as e:
                            # RAW_MATERIAL 반응형 대응 — apply_11st_price_cap.py와 동일(2026-08-27 발견 패턴)
                            body = e.response.text if e.response is not None else ''
                            if 'RAW_MATERIAL' in body and detail.get('origin', {}).get('code'):
                                detail['origin']['code'] = None
                                try:
                                    ok = _put_hulk_update(sess, p.product_no, detail)
                                except Exception as e2:
                                    ok = False
                                    self.stderr.write(f'[{acc.login_id}] {p.product_no} PUT실패(RAW_MATERIAL 재시도후): {e2}')
                            else:
                                ok = False
                                self.stderr.write(f'[{acc.login_id}] {p.product_no} PUT실패: {body[:200]}')
                        except Exception as e:
                            ok = False
                            self.stderr.write(f'[{acc.login_id}] {p.product_no} PUT실패: {e}')
                        if ok:
                            ElevenMyProduct.objects.filter(pk=p.pk).update(status_type='판매중', stock_quantity=new_qty)
                            fixed += 1
                            self.stdout.write(f'{acc.login_id} {p.seller_product_code} {p.product_name[:30]} → 판매중(재고{new_qty})')
                        else:
                            errors += 1
                        time.sleep(0.5)

                    self.stdout.write(f'[{acc.login_id}] 진행 {min(i + chunk_size, len(items))}/{len(items)} (수정{fixed}/변경없음{unchanged}/옵션스킵{skipped_option}/미매칭{no_match}/오류{errors})')
            finally:
                try:
                    sess.close()
                except Exception:
                    pass
                stop_display()

        self.stdout.write(self.style.SUCCESS(
            f'=== 완료: 수정(품절→판매중) {fixed} / 변경없음 {unchanged} / 옵션상품스킵 {skipped_option} / 오너클랜미매칭 {no_match} / 오류 {errors} ==='
        ))
