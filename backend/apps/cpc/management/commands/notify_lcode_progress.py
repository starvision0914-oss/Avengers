"""도매마트 L코드 판매중/품절 조회 진행상황 → 텔레그램 (사용자 요청, 1시간마다).
중지 상태를 그냥 보고만 하면 아무도 안 눌러줄 때 계속 멈춰있게 된다(2026-08-22 9시간 방치 실측)
— 중지 감지 시 알림과 함께 자동으로 재개시킨다."""
import re
import subprocess
from django.core.management.base import BaseCommand

_PROGRESS_LOG = '/tmp/check_domemart_lcodes.log'
_LINE_RE = re.compile(r'^(\d[\d,]*)/(\d[\d,]*) 진행 중\.\.\.$')
_DONE_RE = re.compile(r'^완료: (\d[\d,]*)/(\d[\d,]*) 처리$')


def _real_run_progress():
    """/tmp/check_domemart_lcodes.log에서 '이번 재점검 실행분'의 실제 진행률(done, total)을 읽는다.
    LCodeStatus 전체건수 기반 계산은 '한 번이라도 조회된 적 있는 코드' 비율이라 항상 ~100%로 찍히는
    버그가 있었음(2026-08-27 실측: 실제 58% 진행인데 텔레그램엔 100.0%로 표시돼 사용자가 완료로 오인).
    로그의 마지막 진행률/완료 줄을 그대로 신뢰하는 편이 실제 처리량과 정확히 일치한다."""
    try:
        tail = subprocess.run(['tail', '-n', '300', _PROGRESS_LOG],
                               capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return None
    done = total = None
    is_finished = False
    for line in tail.splitlines():
        line = line.strip()
        m = _DONE_RE.match(line)
        if m:
            done, total = int(m.group(1).replace(',', '')), int(m.group(2).replace(',', ''))
            # (2026-08-29) '완료: X/Y 처리' 줄은 진짜 전체완료뿐 아니라 연속3회실패 등으로 조기중단됐을
            # 때도 똑같이 찍힌다 — X==Y일 때만 진짜 완료로 인정. 아니면 워치독이 죽은 프로세스를
            # '이미 다 끝남'으로 오판해 56분+ 방치하는 사고가 실제로 있었음(2026-08-29 21:47 크롬연결끊김).
            is_finished = (done == total)
            continue
        m = _LINE_RE.match(line)
        if m:
            done, total, is_finished = int(m.group(1).replace(',', '')), int(m.group(2).replace(',', '')), False
    if done is None:
        return None
    return done, total, is_finished


class Command(BaseCommand):
    help = 'L코드(도매마트) 조회 진행상황 텔레그램 알림 + 중지 시 자동재개'

    def add_arguments(self, parser):
        parser.add_argument('--watchdog', action='store_true',
                             help='잦은 주기(10분)용 — 정상 실행 중이면 텔레그램 생략, 재개시켰을 때만 발송')

    def handle(self, *args, **opts):
        from apps.cpc.eleven_my_product_service import get_all_l_codes
        from apps.cpc.models import LCodeStatus
        from apps.cpc import eleven_block_guard as guard
        from apps.cpc.views import _crawl_lock_busy, LCODE_LOCKFILE

        all_codes = get_all_l_codes()
        counts = {'in_stock': 0, 'soldout': 0, 'not_found': 0}
        for row in LCodeStatus.objects.filter(l_code__in=all_codes).values('status'):
            if row['status'] in counts:
                counts[row['status']] += 1
        _, running = _crawl_lock_busy(LCODE_LOCKFILE)

        progress = _real_run_progress()
        if progress:
            checked, total, log_done = progress
            pct = round(checked / total * 100, 1) if total else 0
            done = log_done and not running   # 로그가 완료를 찍었고 프로세스도 실제로 안 살아있을 때만 진짜 완료
        else:
            # 로그를 못 읽으면(로그파일 소실 등) 예전엔 '한 번이라도 조회된 적 있는 코드' 비율로
            # 폴백해 recheck_days(14일) 경과분을 전혀 고려 안 하고 거의 항상 done=True로 오판했음
            # (2026-09-09 발견: /tmp/check_domemart_lcodes.log가 사라진 뒤 이 경로를 타면서
            #  재점검 대상이 3만건 넘게 쌓였는데도 계속 '완료'로 찍혀 도매마트 재점검이
            #  2026-09-06부터 사흘 가까이 멈춰있었음). check_domemart_lcodes와 동일 기준
            #  (미확인 + 14일 경과)으로 남은 작업이 있는지 계산해야 자동재개가 실제로 동작한다.
            from django.utils import timezone as _tz
            total = len(all_codes)
            rows = {r['l_code']: r['checked_at']
                    for r in LCodeStatus.objects.filter(l_code__in=all_codes).values('l_code', 'checked_at')}
            cutoff = _tz.now() - _tz.timedelta(days=14)
            never_checked = total - len(rows)
            stale = sum(1 for ts in rows.values() if ts < cutoff)
            pending = never_checked + stale
            checked = len(rows)
            pct = round(checked / total * 100, 1) if total else 0
            done = pending == 0 and not running
        resumed = False
        if not running and not done:
            try:
                # (2026-08-30) 재개시 옵션 없이 기본값(status_filter=True, recheck_days=14)으로
                # 띄워서, --all-status --recheck-days 0 같은 특수 옵션으로 돌던 전체재조회가
                # 죽었다 재개될 때 "할 일 없음"으로 조용히 끝나버리던 사고 재발방지 — check_domemart_lcodes가
                # 시작할 때 자기 옵션을 남겨둔 마커 파일이 있으면 그대로 재사용해 재개한다.
                cmd = ['python3', 'manage.py', 'check_domemart_lcodes']
                try:
                    with open('/tmp/check_domemart_lcodes.cmdline', encoding='utf-8') as f:
                        saved_args = f.read().split()
                    if saved_args:
                        cmd = ['python3', 'manage.py', 'check_domemart_lcodes'] + saved_args
                except FileNotFoundError:
                    pass
                subprocess.Popen(
                    cmd,
                    stdout=open('/tmp/check_domemart_lcodes.log', 'a'),
                    stderr=subprocess.STDOUT, start_new_session=True)
                resumed = True
            except Exception as e:
                self.stderr.write(f'자동재개 실패: {e}')

        if running:
            status_line = '실행 중'
        elif done:
            status_line = '✅ 완료'
        elif resumed:
            status_line = '⛔ 중지 감지 → 자동 재개함'
        else:
            status_line = '⛔ 중지됨(재개 실패)'
        body = (
            f"🛒 [L코드 조회 진행상황]\n"
            f"{status_line} · {checked:,}/{total:,}건 ({pct}%)\n"
            f"판매중 {counts['in_stock']:,} · 품절 {counts['soldout']:,} · 미확인 {counts['not_found']:,}"
        )
        # watchdog(10분 주기)는 정상 실행 중이거나 이미 완료된 상태(더 할 일 없음)면 조용히 넘어가고,
        # 재개시켰을 때만 알림(완료 알림 자체는 1시간 주기 cron_lcode_progress가 담당)
        skip_alert = opts.get('watchdog') and (running or done)
        if not skip_alert:
            try:
                guard._send_telegram_alert(body)
            except Exception as e:
                self.stderr.write(f'텔레그램 발송 실패: {e}')
        self.stdout.write(body)
