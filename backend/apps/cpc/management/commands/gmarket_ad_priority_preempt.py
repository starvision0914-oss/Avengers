"""지마켓 광고 정기크론 전용 강제선점(2026-08-27 사용자 요청).
16~20시대 광고 크론(광고비수집/간편·일반·AI광고 제어)은 반드시 정시 실행돼야 하므로,
그 시각에 돌고 있는 다른 지마켓 작업을 무엇이든 강제종료하고 락을 비운다.
종료된 작업의 원래 커맨드라인은 큐에 저장해뒀다가, 광고크론이 끝나면
gmarket_resume_preempted로 그대로 재실행한다.

사용법: 광고크론 셸스크립트 맨 앞에서 호출 → 곧바로 실제 광고 크롤/제어 커맨드 실행."""
import os
from django.core.management.base import BaseCommand

# 사용자 지시: 광고 정기크론은 '지마켓 관련 작업이면 무엇이든' 강제종료 가능(범위 넓게).
# 대신 커맨드명에 'gmarket'이 없는(=지마켓과 무관 확실한) 것과, 아래 상시 서비스는 절대 제외.
# (2026-08-27 실측 사고: r'manage\.py \w+' 로 넓게 잡았다가 runserver/telegram_command_bot/
#  sms_adb_poller까지 죽임. PM2가 즉시 재기동해 실피해는 없었지만 재발 방지 위해 명시적 화이트리스트로 전환.)
_EXTRA_GMARKET_CMDS = ('run_ai_schedule',)   # 커맨드명에 'gmarket'이 없지만 지마켓 전용인 것들
# PM2 등으로 상시 구동되는 핵심 서비스 — 어떤 경우에도 죽이지 않음(최종 안전장치, 최우선 적용)
_NEVER_KILL_SUBSTRINGS = ('runserver', 'telegram_command_bot', 'sms_adb_poller', 'celery',
                          'gmarket_ad_priority_preempt', 'gmarket_resume_preempted')


def _is_gmarket_ad_cmd(cmdline):
    joined = ' '.join(cmdline)
    if any(s in joined for s in _NEVER_KILL_SUBSTRINGS):
        return False
    if 'manage.py' not in joined:
        return False
    return 'gmarket' in joined.lower() or any(w in joined for w in _EXTRA_GMARKET_CMDS)


class Command(BaseCommand):
    help = '지마켓 광고 정기크론 실행 전, 돌고있는 다른 지마켓 작업을 강제종료(선점)'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='종료 없이 대상만 출력')

    def handle(self, *args, **opts):
        from apps.cpc import eleven_block_guard as guard

        self.dry_run = opts['dry_run']
        my_pid = os.getpid()
        killed_any = False
        handled_pids = set()

        # 1) 락파일이 가리키는 PID — 화이트리스트 재검증 후에만 종료(락파일이 잘못된 걸 가리켜도 안전)
        lock = guard._lock_path('gmarket')
        if lock.exists():
            try:
                parts = lock.read_text(encoding='utf-8').strip().split('|')
                pid = int(parts[0]); holder_name = parts[1] if len(parts) > 1 else '?'
            except Exception:
                pid, holder_name = 0, '?'
            if pid and pid != my_pid and guard._pid_alive(pid):
                try:
                    with open(f'/proc/{pid}/cmdline', 'rb') as f:
                        raw = f.read()
                    cmdline = [x for x in raw.decode('utf-8', errors='replace').split('\x00') if x]
                except Exception:
                    cmdline = []
                if cmdline and _is_gmarket_ad_cmd(cmdline):
                    self._kill_and_queue(guard, pid, holder_name, cmdline_override=cmdline)
                    killed_any = True
                    handled_pids.add(pid)
                else:
                    self.stdout.write(f'⚠ 락 보유 PID {pid}가 지마켓 광고 커맨드가 아님 — 종료 안 함(cmdline={cmdline})')
            if not self.dry_run:
                try:
                    lock.unlink()
                except Exception:
                    pass

        # 2) 락파일에 안 잡혀도 돌고 있을 수 있는 다른 지마켓 광고 프로세스(화이트리스트만, 안전망)
        for pid_dir in os.listdir('/proc'):
            if not pid_dir.isdigit():
                continue
            pid = int(pid_dir)
            if pid == my_pid or pid in handled_pids:
                continue
            try:
                with open(f'/proc/{pid}/cmdline', 'rb') as f:
                    raw = f.read()
                cmdline = [x for x in raw.decode('utf-8', errors='replace').split('\x00') if x]
            except Exception:
                continue
            if not cmdline or not _is_gmarket_ad_cmd(cmdline):
                continue
            self._kill_and_queue(guard, pid, ' '.join(cmdline)[:60], cmdline_override=cmdline)
            killed_any = True
            handled_pids.add(pid)

        # 광고제어 전용 busy마커도 같이 비움 — 이게 남아있으면 try_acquire_adcontrol()이
        # '이미 실행 중'으로 오판해 스킵함(2026-08-27 16:22 간편광고 OFF 스킵 사고의 원인).
        if not self.dry_run:
            try:
                guard.clear_adcontrol_busy('gmarket')
            except Exception:
                pass

        if killed_any:
            self.stdout.write(self.style.SUCCESS('강제선점 완료 — 다른 지마켓 작업 종료 후 락 비움'))
        else:
            self.stdout.write('선점 불필요 — 돌고 있는 다른 작업 없음')

    def _kill_and_queue(self, guard, pid, holder_name, cmdline_override=None):
        cmdline = cmdline_override
        if cmdline is None:
            try:
                with open(f'/proc/{pid}/cmdline', 'rb') as f:
                    raw = f.read()
                cmdline = [x for x in raw.decode('utf-8', errors='replace').split('\x00') if x]
            except Exception:
                cmdline = None
        if self.dry_run:
            self.stdout.write(f'[DRY-RUN] ⛔ {holder_name}(pid={pid}) 종료 대상(실행 안 함) cmdline={cmdline}')
            return
        self.stdout.write(f'⛔ {holder_name}(pid={pid}) 강제종료')
        killed = guard._kill_pid_gracefully(pid)
        if not killed:
            self.stdout.write(f'⚠ {holder_name}(pid={pid}) 강제종료 확인 실패')
        if cmdline:
            guard._queue_preempted('gmarket', cmdline, holder_name)
