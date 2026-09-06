"""11번가 상품명 끝에 도매처 원본데이터가 흘러들어온 날짜(YY.MM.DD, 예: '26.08.28')를
잘라내는 일괄 정리. hulk API(optimize_11st_product_names.py에서 검증된
_get_session/_get_hulk_detail/_put_hulk_update)로 productName만 갱신한다.

패턴: '단짝 46g(1타 12개입) 26.08.28' → '단짝 46g(1타 12개입)'
      '호올스...(1타 20개입) 26.10.16/대용량사탕/할로윈간식' → '호올스...(1타 20개입)/대용량사탕/할로윈간식'
      (날짜 앞 공백까지 함께 제거해 뒤따르는 '/태그' 목록은 그대로 보존)

날짜는 최신 hulk API 응답의 productName 기준으로 다시 확인 후 잘라낸다(DB 스냅샷이 이미
바뀌었을 수 있으므로 — 상품명이 이미 수정됐거나 패턴이 없으면 스킵).

사용법:
  python manage.py trim_11st_date_from_name --dry-run
  python manage.py trim_11st_date_from_name
  python manage.py trim_11st_date_from_name --account rejoice321
"""
import re
import time

from django.core.management.base import BaseCommand

_DATE_RE = re.compile(r'\d{2}\.(0[1-9]|1[0-2])\.(0[1-9]|[12]\d|3[01])(?!\d)')
_STRIP_RE = re.compile(r'\s*' + _DATE_RE.pattern)


def _trim(name: str) -> str:
    new = _STRIP_RE.sub('', name or '').strip()
    return re.sub(r'\s{2,}', ' ', new)


class Command(BaseCommand):
    help = "11번가 상품명에 남은 날짜(YY.MM.DD)를 잘라내는 일괄 정리"

    def add_arguments(self, parser):
        parser.add_argument('--account', help='특정 11번가 login_id만')
        parser.add_argument('--dry-run', action='store_true', help='실제 반영 없이 대상만 출력')

    def handle(self, *args, **opts):
        import requests
        from apps.cpc.models import ElevenMyProduct, protected_login_ids
        from apps.cpc.management.commands.optimize_11st_product_names import (
            _get_session, _get_hulk_detail, _put_hulk_update,
        )
        from apps.cpc import eleven_block_guard as guard

        dry_run = opts['dry_run']

        protected = protected_login_ids('11st')
        qs = ElevenMyProduct.objects.exclude(status_type='판매중지').exclude(
            account__login_id__in=protected).select_related('account')
        if opts['account']:
            qs = qs.filter(account__login_id=opts['account'])

        products = [p for p in qs if _DATE_RE.search(p.product_name or '')]
        by_account = {}
        for p in products:
            by_account.setdefault(p.account_id, {'account': p.account, 'items': []})['items'].append(p)
        self.stdout.write(f'대상: {len(products)}건 / {len(by_account)}계정')

        # dry-run도 실제 로그인(hulk 조회)이 필요해 락 보호 필수(11st 동시크롤 금지).
        ok, reason = guard.preflight('11st_trim_date_name', wait=True, platform='11st')
        if not ok:
            self.stdout.write(self.style.WARNING(f'⏭️ 건너뜀 — {reason}'))
            return

        fixed = skipped = errors = 0
        try:
            for acc_id, group in by_account.items():
                acc = group['account']
                items = group['items']
                self.stdout.write(f'[{acc.login_id}] {len(items)}건 처리 시작')
                try:
                    sess = _get_session(acc)
                except Exception as e:
                    self.stderr.write(f'[{acc.login_id}] 로그인 실패: {e}')
                    errors += len(items)
                    continue
                try:
                    for p in items:
                        try:
                            detail = _get_hulk_detail(sess, p.product_no)
                        except Exception as e:
                            self.stderr.write(f'[{acc.login_id}] {p.product_no} 조회실패: {e}')
                            errors += 1
                            continue
                        cur_name = detail.get('productName', '')
                        new_name = _trim(cur_name)
                        if not _DATE_RE.search(cur_name) or new_name == cur_name:
                            skipped += 1
                            continue
                        if dry_run:
                            self.stdout.write(f'[dry-run] {acc.login_id} {p.product_no}\n  전: {cur_name}\n  후: {new_name}')
                            fixed += 1
                            continue
                        detail['productName'] = new_name
                        try:
                            success = _put_hulk_update(sess, p.product_no, detail)
                        except requests.exceptions.HTTPError as e:
                            body = e.response.text if e.response is not None else ''
                            if 'RAW_MATERIAL' in body and detail.get('origin', {}).get('code'):
                                detail['origin']['code'] = None
                                try:
                                    success = _put_hulk_update(sess, p.product_no, detail)
                                except Exception as e2:
                                    success = False
                                    self.stderr.write(f'[{acc.login_id}] {p.product_no} PUT실패(RAW_MATERIAL후): {e2}')
                            else:
                                success = False
                                self.stderr.write(f'[{acc.login_id}] {p.product_no} PUT실패: {body[:200]}')
                        except Exception as e:
                            success = False
                            self.stderr.write(f'[{acc.login_id}] {p.product_no} PUT실패: {e}')
                        if success:
                            ElevenMyProduct.objects.filter(pk=p.pk).update(product_name=new_name)
                            self.stdout.write(f'{acc.login_id} {p.product_no}: {new_name[:50]} → 저장완료')
                            fixed += 1
                        else:
                            errors += 1
                        time.sleep(0.5)
                finally:
                    pass
        finally:
            guard.release_global_lock(platform='11st')

        self.stdout.write(self.style.SUCCESS(f'=== 완료: 수정 {fixed} / 스킵(이미변경됨) {skipped} / 오류 {errors} ==='))
