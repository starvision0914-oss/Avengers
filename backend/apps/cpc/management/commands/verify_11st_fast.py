"""11번가 빠른 OTP 인증 커맨드.

개선:
  1. requests로 쿠키 유효성 체크 (Chrome 없이, 계정당 ~1초)
  2. 만료된 계정만 Chrome 1개 재사용해 OTP 처리 (계정 간 quit 없음)

Usage:
    python3 manage.py verify_11st_fast [--only rejoice666,starvisi] [--force]

--force: 유효성 체크 없이 전계정 재인증
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests as req_lib
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.cpc.models import CrawlerAccount
from crawlers.browser import create_driver
from crawlers.eleven_crawler import _do_login, _save_cookies

CHECK_URL = 'https://soffice.11st.co.kr/view/main'
OTP_KEYWORDS = ('otpLoginForm', 'otp', 'auth_type_01')
COOKIE_CHECK_TIMEOUT = 6


def _cookie_valid(account) -> bool:
    """requests로 쿠키 유효성 빠른 체크. True=유효, False=만료."""
    if not account.cookie_data:
        return False
    try:
        cookies = json.loads(account.cookie_data)
        jar = {c['name']: c['value'] for c in cookies}
        resp = req_lib.get(
            CHECK_URL, cookies=jar,
            allow_redirects=False, timeout=COOKIE_CHECK_TIMEOUT,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        return resp.status_code == 200
    except Exception:
        return False


class Command(BaseCommand):
    help = '11번가 빠른 OTP 인증 (쿠키 체크 → 만료된 것만 Chrome OTP)'

    def add_arguments(self, parser):
        parser.add_argument('--only', type=str, default='')
        parser.add_argument('--force', action='store_true',
                            help='쿠키 체크 생략, 전계정 재인증')
        parser.add_argument('--out', type=str, default='/tmp/11st_fast_result.json')

    def handle(self, *args, **opts):
        qs = CrawlerAccount.objects.filter(
            platform='11st', is_active=True
        ).order_by('display_order', 'id')

        if opts['only']:
            want = {x.strip() for x in opts['only'].split(',') if x.strip()}
            qs = qs.filter(login_id__in=want)

        accounts = list(qs)
        total = len(accounts)
        self.stdout.write(f'[fast-verify] 대상: {total}개')

        # ── Step 1: 쿠키 유효성 체크 ──
        need_otp = []
        skip_count = 0

        if opts['force']:
            need_otp = accounts
            self.stdout.write('--force: 전계정 재인증')
        else:
            self.stdout.write('\n[Step 1] 쿠키 유효성 체크 중...')
            for i, acct in enumerate(accounts, 1):
                valid = _cookie_valid(acct)
                status = '✅ 유효' if valid else '❌ 만료'
                self.stdout.write(f'  [{i}/{total}] {acct.login_id:<22} {status}')
                self.stdout.flush()
                if not valid:
                    need_otp.append(acct)
                else:
                    skip_count += 1

            self.stdout.write(
                f'\n체크 완료 — 유효: {skip_count}개 스킵 / 만료: {len(need_otp)}개 OTP 필요\n'
            )

        if not need_otp:
            self.stdout.write('✅ 모든 쿠키 유효. OTP 인증 불필요.')
            return

        # ── Step 2: 만료 계정만 Chrome 1개로 순서대로 OTP ──
        self.stdout.write(f'[Step 2] Chrome OTP 처리: {len(need_otp)}개')
        results = []
        driver = None

        try:
            driver = create_driver()

            for i, acct in enumerate(need_otp, 1):
                self.stdout.write(
                    f'\n  [{i}/{len(need_otp)}] {acct.login_id} ({acct.seller_name})'
                )
                self.stdout.flush()
                t0 = time.time()
                entry = {
                    'login_id': acct.login_id,
                    'seller_name': acct.seller_name,
                    'status': 'unknown',
                    'message': '',
                }

                try:
                    # 이전 계정 쿠키 정리
                    try:
                        driver.delete_all_cookies()
                    except Exception:
                        pass

                    ok = _do_login(driver, acct.login_id, acct.password_enc)

                    final_url = ''
                    try:
                        final_url = driver.current_url
                    except Exception:
                        pass

                    if ok:
                        entry['status'] = 'success'
                        entry['message'] = final_url
                        try:
                            _save_cookies(driver, acct)
                            self.stdout.write(f'    ✅ 성공 (쿠키 저장)')
                        except Exception as e:
                            self.stdout.write(f'    ✅ 성공 (⚠️ 쿠키저장 실패: {e})')
                    else:
                        lower = (final_url or '').lower()
                        if any(k.lower() in lower for k in OTP_KEYWORDS):
                            entry['status'] = 'otp_required'
                            entry['message'] = f'OTP 미완: {final_url}'
                            self.stdout.write(f'    ⚠️ OTP 미완')
                        else:
                            entry['status'] = 'failed'
                            entry['message'] = final_url or 'login returned False'
                            self.stdout.write(f'    ❌ 실패: {entry["message"]}')

                except Exception as exc:
                    entry['status'] = 'error'
                    entry['message'] = str(exc)
                    self.stdout.write(f'    💥 오류: {exc}')
                    # Chrome이 죽었으면 재시작
                    try:
                        driver.current_url
                    except Exception:
                        self.stdout.write('    [Chrome 재시작]')
                        try:
                            driver.quit()
                        except Exception:
                            pass
                        driver = create_driver()

                entry['elapsed'] = round(time.time() - t0, 1)
                results.append(entry)

                try:
                    Path(opts['out']).write_text(
                        json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8'
                    )
                except Exception:
                    pass

        finally:
            try:
                if driver:
                    driver.quit()
            except Exception:
                pass

        # ── 결과 요약 ──
        summary = {
            'total_checked': total,
            'skipped_valid': skip_count,
            'otp_attempted': len(need_otp),
            'success': sum(1 for r in results if r['status'] == 'success'),
            'failed': sum(1 for r in results if r['status'] == 'failed'),
            'otp_required': sum(1 for r in results if r['status'] == 'otp_required'),
            'error': sum(1 for r in results if r['status'] == 'error'),
        }
        self.stdout.write('\n========== 결과 요약 ==========')
        self.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2))

        failed = [r for r in results if r['status'] != 'success']
        if failed:
            self.stdout.write('\n실패 계정:')
            for r in failed:
                self.stdout.write(f'  {r["status"]:14s} {r["login_id"]}')

        # 텔레그램 통보
        try:
            msg = (
                f'✅ [11번가 빠른 OTP 갱신 완료]\n'
                f'전체: {total}개 | 스킵(유효): {skip_count}개\n'
                f'OTP처리: {len(need_otp)}개 → 성공: {summary["success"]} / 실패: {summary["failed"]}'
            )
            if failed:
                msg += '\n실패: ' + ', '.join(r['login_id'] for r in failed)
            import os
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
            from apps.cpc.eleven_block_guard import _send_telegram_alert
            _send_telegram_alert(msg)
        except Exception:
            pass

        self.stdout.write(f'\n결과 JSON: {opts["out"]}')
