"""11번가 셀레늄 작업들을 직렬 실행 — chrome 동시 실행 충돌 방지.

`integrated-sync` 호출 시 grade/cost/office 가 동시에 띄어지면 각자
`_kill_stale_chrome()` 으로 서로의 chrome 을 죽이는 race condition 발생.
이 command 는 셀레늄 작업들을 한 프로세스에서 순서대로 실행한다.

실행 모드:
    python manage.py run_11st_selenium_chain --tasks grade,cost,office
    python manage.py run_11st_selenium_chain --tasks grade,cost
"""
import os
import sys
import time
import traceback
from datetime import datetime

from django.core.management.base import BaseCommand
from django.core.management import call_command

LOG_PATH = '/tmp/cron_11st_selenium_chain.log'


def _log(msg):
    line = f'[{datetime.now().strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


class Command(BaseCommand):
    help = '11번가 셀레늄 작업 직렬 실행 (grade/cost/office)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tasks',
            type=str,
            default='grade,cost,office',
            help='실행할 작업 (콤마 구분): grade, cost, office',
        )
        parser.add_argument(
            '--account-id',
            type=int,
            default=None,
            help='특정 계정만 (office 용)',
        )

    def handle(self, *args, **opts):
        from apps.cpc import eleven_block_guard as guard

        tasks_raw = (opts.get('tasks') or '').strip()
        tasks = [t.strip() for t in tasks_raw.split(',') if t.strip()]
        valid = {'grade', 'cost', 'office'}
        tasks = [t for t in tasks if t in valid]

        if not tasks:
            _log('실행할 작업 없음')
            return

        # 시작 시점 글로벌 차단 체크
        blocked, remaining, until = guard.is_blocked()
        if blocked:
            _log(f'⛔ 글로벌 차단 모드 — 셀레늄 체인 전체 스킵 ({remaining}초 후 해제)')
            return

        account_id = opts.get('account_id')

        _log(f'==== 11번가 셀레늄 체인 시작: {", ".join(tasks)} ====')
        from crawlers.browser import _kill_stale_chrome, stop_display

        # 시작 전 좀비 chrome 정리 (한 번만)
        _kill_stale_chrome()

        for task in tasks:
            # 매 task 사이에도 차단 체크 (이전 task에서 차단 락 걸렸을 수 있음)
            blocked, remaining, _ = guard.is_blocked()
            if blocked:
                _log(f'⛔ 이전 task 후 글로벌 차단 — 남은 task 스킵 ({remaining}초 남음)')
                break

            _log(f'--- task 시작: {task} ---')
            t0 = time.time()
            try:
                if task == 'grade':
                    call_command('crawl_11st_grade')
                elif task == 'cost':
                    call_command('crawl_11st_cost')
                elif task == 'office':
                    if account_id:
                        call_command('crawl_11st_office', account_id=account_id)
                    else:
                        call_command('crawl_11st_office', all_focused=True)
            except Exception as e:
                _log(f'[{task}] 예외: {e}')
                _log(traceback.format_exc()[-1500:])

            elapsed = time.time() - t0
            _log(f'--- task 완료: {task} ({elapsed:.1f}s) ---')

            # 다음 task 전 chrome 완전 정리
            _kill_stale_chrome()
            time.sleep(2)

        # 최종 정리
        try:
            stop_display()
        except Exception:
            pass

        _log(f'==== 11번가 셀레늄 체인 종료 ====')
