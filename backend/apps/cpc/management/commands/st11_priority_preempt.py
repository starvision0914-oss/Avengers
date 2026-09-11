"""11번가 정규크론(광고비수집/상품ROAS 등) 전용 강제선점(2026-09-11 사용자 요청 —
"정규크론은 항상 먼저 돌아가도록 만들어줘". 지마켓의 gmarket_ad_priority_preempt와 동일 취지).

전략설정 가드(guard_11st_ad_schedule_on_spike)나 캠페인조회(list_campaigns) 같은 부가 작업이
락을 오래 쥐고 있으면(계정당 최대 1.5시간+) 정규 크론이 못 돌거나 통째로 스킵되는 사고가
반복돼(2026-09-11 rejoice666 사고) 도입. 정규크론 실행 전 이 커맨드를 먼저 호출하면, 그 시각에
돌고 있는 다른 11번가 작업을 무엇이든 강제종료하고 락을 비운다. 종료된 작업의 원래 커맨드라인은
큐에 저장해뒀다가, 정규크론이 끝나면 st11_resume_preempted로 그대로 재실행한다.

사용법: 정규크론 셸스크립트 맨 앞에서 호출 → 곧바로 실제 정규 크롤 커맨드 실행."""
import os
from django.core.management.base import BaseCommand

# PM2 등으로 상시 구동되는 핵심 서비스 — 어떤 경우에도 죽이지 않음(최종 안전장치, 최우선 적용).
# gmarket_ad_priority_preempt의 2026-08-27 사고(runserver/telegram_command_bot/sms_adb_poller까지
# 오살) 재발 방지 — 여기서도 동일하게 명시적 화이트리스트로만 판단한다.
_NEVER_KILL_SUBSTRINGS = ('runserver', 'telegram_command_bot', 'sms_adb_poller', 'celery',
                          'st11_priority_preempt', 'st11_resume_preempted')


def _is_11st_ad_cmd(cmdline):
    joined = ' '.join(cmdline)
    if any(s in joined for s in _NEVER_KILL_SUBSTRINGS):
        return False
    # 'manage.py'는 실제 실행 인자 토큰이어야 한다(문자열 안에 우연히 포함된 경우 배제) —
    # 예: 모니터링용 bash -c 안의 pgrep 패턴 문자열에 'manage.py guard_11st_...'가 들어있으면
    # 그 bash 프로세스 자체를 11번가 작업으로 오판해 죽이는 사고가 날 수 있다(2026-09-11 실측).
    try:
        idx = cmdline.index('manage.py')
    except ValueError:
        idx = -1
    if idx >= 0:
        sub = cmdline[idx + 1] if idx + 1 < len(cmdline) else ''
        return '11st' in sub.lower() or 'eleven' in sub.lower()
    return any('eleven_ad_strategy.py' in tok for tok in cmdline)


class Command(BaseCommand):
    help = '11번가 정규크론 실행 전, 돌고있는 다른 11번가 작업을 강제종료(선점)'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='종료 없이 대상만 출력')

    def handle(self, *args, **opts):
        from apps.cpc import eleven_block_guard as guard

        self.dry_run = opts['dry_run']
        self.killed_items = []   # (holder_name, pid, cmdline) — 텔레그램/사고기록용
        my_pid = os.getpid()
        killed_any = False
        handled_pids = set()

        # 1) 락파일이 가리키는 PID — 화이트리스트 재검증 후에만 종료
        lock = guard._lock_path('11st')
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
                if cmdline and _is_11st_ad_cmd(cmdline):
                    self._kill_and_queue(guard, pid, holder_name, cmdline_override=cmdline)
                    killed_any = True
                    handled_pids.add(pid)
                else:
                    self.stdout.write(f'⚠ 락 보유 PID {pid}가 11번가 작업이 아님 — 종료 안 함(cmdline={cmdline})')
            if not self.dry_run:
                try:
                    lock.unlink()
                except Exception:
                    pass

        # 2) 락파일에 안 잡혀도 돌고 있을 수 있는 다른 11번가 프로세스(화이트리스트만, 안전망)
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
            if not cmdline or not _is_11st_ad_cmd(cmdline):
                continue
            self._kill_and_queue(guard, pid, ' '.join(cmdline)[:60], cmdline_override=cmdline)
            killed_any = True
            handled_pids.add(pid)

        if killed_any:
            self.stdout.write(self.style.SUCCESS('강제선점 완료 — 다른 11번가 작업 종료 후 락 비움'))
            if not self.dry_run:
                self._record_incident(guard)
        else:
            self.stdout.write('선점 불필요 — 돌고 있는 다른 작업 없음')

    def _record_incident(self, guard):
        """실제로 뭔가 강제종료됐을 때만 기록 — 원인추적용 사고로그 + 텔레그램 알림
        (2026-09-11 사용자 요청: 충돌 발생시 원인파악/개선까지 이어지도록 흔적을 남겨야 함).
        코드를 자동으로 고치는 건 위험해서(검증 없는 자동수정 금지) 하지 않고, 대신 무엇이
        언제 왜 밀렸는지 놓치지 않게 기록만 남긴다 — 반복되는 패턴이면 사람이(또는 다음 세션의
        Claude가) 이 로그를 근거로 근본원인을 고칠 수 있게."""
        import json as _json
        from django.utils import timezone as _tz
        p = '/tmp/avengers_11st_preempt_incidents.log'
        lines = []
        for holder_name, pid, cmdline in self.killed_items:
            rec = {'at': _tz.localtime().isoformat(), 'holder': holder_name, 'pid': pid,
                   'cmdline': ' '.join(cmdline)[:200] if cmdline else None}
            lines.append(_json.dumps(rec, ensure_ascii=False))
        try:
            with open(p, 'a', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n')
        except Exception:
            pass
        names = ', '.join(sorted({h for h, _p, _c in self.killed_items}))
        msg = (f'⚠️ [11번가 정규크론 선점] {names} 강제종료 후 정규크론 우선실행\n'
               f'(종료된 작업은 정규크론 완료 후 재개됨 — 반복되면 근본원인 점검 필요)')
        try:
            guard._send_telegram_alert(msg)
        except Exception:
            pass

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
            guard._queue_preempted('11st', cmdline, holder_name)
        self.killed_items.append((holder_name, pid, cmdline))
