"""11번가 전체 계정 로그인 검증 커맨드.

Usage:
    python3 manage.py verify_11st_logins [--limit 5] [--only rejoice666,starvisi]
                                          [--skip-otp] [--cooldown 3]

각 계정마다 Chrome 드라이버를 새로 띄워 로그인을 시도하고,
OTP가 필요한 경우 기존 crawlers.eleven_crawler._do_login 의
Redis SMS 수신 플로우로 자동 해결합니다.

결과는 stdout 에 실시간 출력되며 JSON 요약이 마지막에 찍힙니다.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.cpc.models import CrawlerAccount
from crawlers.browser import create_driver
from crawlers.eleven_crawler import _do_login, _save_cookies

OTP_KEYWORDS = ('otpLoginForm', 'otp', 'auth_type_01')


def _force_kill_driver(driver):
    """드라이버(크롬드라이버+크롬)가 멈춰서 응답이 없을 때 OS 프로세스를 강제 종료.
    driver.quit()은 죽은 연결에 또 HTTP 요청을 보내 같이 멈출 수 있어 먼저 PID를 직접 kill."""
    pid = None
    try:
        pid = driver.service.process.pid
    except Exception:
        pid = None
    if pid:
        try:
            subprocess.run(['pkill', '-9', '-P', str(pid)], timeout=5)
        except Exception:
            pass
        try:
            os.kill(pid, 9)
        except Exception:
            pass
    try:
        driver.quit()
    except Exception:
        pass


class Command(BaseCommand):
    help = 'Verify login for every 11st CrawlerAccount'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0,
                            help='max accounts to try (0 = all)')
        parser.add_argument('--only', type=str, default='',
                            help='comma-separated login_id filter')
        parser.add_argument('--skip-otp', action='store_true',
                            help='do not wait for SMS OTP — mark as OTP_REQUIRED')
        parser.add_argument('--cooldown', type=float, default=3.0,
                            help='seconds between accounts')
        parser.add_argument('--timeout', type=float, default=180.0,
                            help='계정당 최대 대기 시간(초) — 초과 시 강제종료하고 다음 계정으로 진행')
        parser.add_argument('--out', type=str,
                            default='/tmp/11st_verify_result.json')

    def handle(self, *args, **opts):
        qs = CrawlerAccount.objects.filter(platform='11st').order_by('display_order')
        if opts['only']:
            want = {x.strip() for x in opts['only'].split(',') if x.strip()}
            qs = qs.filter(login_id__in=want)
        if opts['limit'] > 0:
            qs = qs[: opts['limit']]
        accounts = list(qs)
        self.stdout.write(f'[verify] target accounts: {len(accounts)}')

        results = []
        started = time.time()

        for i, acct in enumerate(accounts, start=1):
            entry = {
                'idx': i,
                'order': acct.display_order,
                'login_id': acct.login_id,
                'seller_name': acct.seller_name,
                'status': 'unknown',
                'message': '',
                'elapsed': 0.0,
                'otp_required': False,
            }
            t0 = time.time()
            self.stdout.write(
                f'\n[{i}/{len(accounts)}] {acct.login_id} ({acct.seller_name}) — 시도')
            self.stdout.flush()

            # 크롬드라이버가 죽거나 응답불능이 되면 셀레니움 호출이 무한정 멈출 수 있음
            # (Selenium 4.x의 command_executor 타임아웃은 드라이버 생성 후 연결풀에
            # 소급 적용되지 않는 결함이 있어 실효가 없었음, 2026-07-19 확인).
            # 별도 스레드에서 실행하고 메인 스레드에서 --timeout(기본 180초)으로 하드컷 —
            # 초과 시 강제로 프로세스를 죽이고 다음 계정으로 넘어간다(무한 대기 방지).
            holder = {}

            def _attempt(_acct=acct, _holder=holder):
                d = create_driver()
                _holder['driver'] = d
                _ok = _do_login(d, _acct.login_id, _acct.password_enc)
                return _ok

            driver = None
            timed_out = False
            try:
                with ThreadPoolExecutor(max_workers=1) as ex:
                    fut = ex.submit(_attempt)
                    try:
                        ok = fut.result(timeout=opts['timeout'])
                    except FutureTimeoutError:
                        timed_out = True
                        ok = False
                    except BaseException as exc:
                        # 외부 인터럽트(SIGINT 등) 포함 — 이 계정만 실패 처리하고 배치는 계속.
                        ok = False
                        entry['message'] = f'interrupted: {exc!r}'

                driver = holder.get('driver')

                if timed_out:
                    entry['status'] = 'timeout'
                    entry['message'] = f'{opts["timeout"]:.0f}초 초과 — 강제종료'
                    self.stdout.write(f'  ⏱️ 타임아웃({opts["timeout"]:.0f}초) — 강제종료 후 다음 계정')
                    _force_kill_driver(driver)
                    driver = None   # 이미 강제종료했으니 아래 finally에서 재시도하지 않음
                else:
                    final_url = ''
                    try:
                        final_url = driver.current_url if driver else ''
                    except Exception:
                        pass

                    if ok:
                        entry['status'] = 'success'
                        entry['message'] = final_url
                        # ★ OTP 성공 세션을 쿠키로 저장 — 안 하면 last_otp_at만 갱신되고
                        #   세션이 버려져 "OTP완료인데 인증 안됨"(다음 크롤이 또 OTP) 발생.
                        try:
                            _save_cookies(driver, acct)
                            self.stdout.write(f'  ✅ 성공 → {final_url} (쿠키 저장)')
                        except Exception as _e:
                            self.stdout.write(f'  ✅ 성공 → {final_url} (⚠️ 쿠키저장 실패: {_e})')
                    else:
                        # OTP 페이지에 머물렀는지 확인
                        lower = (final_url or '').lower()
                        if any(k.lower() in lower for k in OTP_KEYWORDS):
                            entry['status'] = 'otp_required'
                            entry['otp_required'] = True
                            entry['message'] = f'OTP 미완: {final_url}'
                            self.stdout.write(f'  ⚠️ OTP 필요 / 실패 → {final_url}')
                        else:
                            entry['status'] = entry['status'] if entry['status'] != 'unknown' else 'failed'
                            if not entry['message']:
                                entry['message'] = final_url or 'login returned False'
                            self.stdout.write(f'  ❌ 실패 → {entry["message"]}')
            except Exception as exc:
                entry['status'] = 'error'
                entry['message'] = f'driver error: {exc}'
                self.stdout.write(f'  💥 드라이버 오류: {exc}')
            finally:
                if driver is not None:
                    try:
                        driver.quit()
                    except Exception:
                        pass
                entry['elapsed'] = round(time.time() - t0, 1)
                results.append(entry)

                # Snapshot 저장 (중간 중단 대비)
                try:
                    Path(opts['out']).write_text(
                        json.dumps(results, ensure_ascii=False, indent=2),
                        encoding='utf-8',
                    )
                except Exception:
                    pass

                time.sleep(opts['cooldown'])

        elapsed = round(time.time() - started, 1)
        summary = {
            'total': len(results),
            'success': sum(1 for r in results if r['status'] == 'success'),
            'failed': sum(1 for r in results if r['status'] == 'failed'),
            'otp_required': sum(1 for r in results if r['status'] == 'otp_required'),
            'error': sum(1 for r in results if r['status'] == 'error'),
            'timeout': sum(1 for r in results if r['status'] == 'timeout'),
            'elapsed_sec': elapsed,
        }
        self.stdout.write('\n========== 결과 요약 ==========')
        self.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2))
        self.stdout.write('\n실패/OTP 필요 계정:')
        for r in results:
            if r['status'] not in ('success',):
                self.stdout.write(
                    f'  {r["status"]:14s} {r["login_id"]:20s} '
                    f'({r["seller_name"]}) — {r["message"]}'
                )
        self.stdout.write(f'\n결과 JSON: {opts["out"]}')
