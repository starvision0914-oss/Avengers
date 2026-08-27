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
            done, total, is_finished = int(m.group(1).replace(',', '')), int(m.group(2).replace(',', '')), True
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
            # 로그를 못 읽으면(최초 실행 등) 예전 방식으로 폴백 — 부정확할 수 있음을 감안
            total = len(all_codes)
            checked = LCodeStatus.objects.filter(l_code__in=all_codes).count()
            pct = round(checked / total * 100, 1) if total else 0
            done = checked >= total and not running
        resumed = False
        if not running and not done:
            try:
                subprocess.Popen(
                    ['python3', 'manage.py', 'check_domemart_lcodes'],
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
