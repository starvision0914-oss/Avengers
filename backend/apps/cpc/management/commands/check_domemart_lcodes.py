"""도매마트(domemart.co.kr) L코드 판매상태 대량 조회 — 재개 가능(체크포인트=DB에 upsert).
누를 때마다 이어서: LCodeStatus에 아직 없는 코드부터, 그 다음 오래된 것부터 재확인.
사람 페이싱(코드당 1~2.5초) — 16만개는 하루에 다 못 돌리므로 백그라운드에서 계속 실행,
락 파일 제거로 중단 신호를 받는다(St11CrawlStopView 패턴과 동일).
"""
import os
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

LOCKFILE = '/tmp/avengers_domemart_lcode.lock'


class Command(BaseCommand):
    help = '도매마트 L코드 판매중/품절 상태 조회(재개 가능)'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0, help='이번 실행에서 최대 몇 건 처리(0=무제한, 락 제거될 때까지)')
        parser.add_argument('--recheck-days', type=int, default=14, help='이 일수보다 오래된 기존 결과도 재확인 대상에 포함')

    def handle(self, *args, **opts):
        from apps.cpc.eleven_my_product_service import get_all_l_codes
        from apps.cpc.models import LCodeStatus
        from crawlers import domemart_crawler as dm

        # 락 획득 — 이미 실행 중이면 즉시 종료
        if os.path.exists(LOCKFILE):
            try:
                pid = int((open(LOCKFILE).read() or '0').split('|')[0].strip() or 0)
                os.kill(pid, 0)
                self.stdout.write(self.style.WARNING(f'이미 실행 중(PID={pid}) — 종료'))
                return
            except (OSError, ValueError):
                pass  # stale, 이어서 진행
        with open(LOCKFILE, 'w') as f:
            f.write(f'{os.getpid()}|domemart_lcode|{timezone.now().isoformat()}')

        try:
            self._run(opts, get_all_l_codes, LCodeStatus, dm)
        finally:
            try:
                cur = int((open(LOCKFILE).read() or '0').split('|')[0].strip() or 0)
                if cur == os.getpid():
                    os.remove(LOCKFILE)
            except Exception:
                pass

    def _run(self, opts, get_all_l_codes, LCodeStatus, dm):
        import random

        all_codes = get_all_l_codes()
        existing = {r['l_code']: r['checked_at'] for r in LCodeStatus.objects.values('l_code', 'checked_at')}
        now = timezone.now()
        recheck_cutoff = now - timezone.timedelta(days=opts['recheck_days'])

        never_checked = sorted(c for c in all_codes if c not in existing)
        stale = sorted(c for c in all_codes if c in existing and existing[c] < recheck_cutoff)
        pending = never_checked + stale
        limit = opts['limit'] or len(pending)
        pending = pending[:limit]

        self.stdout.write(f'전체 L코드 {len(all_codes)} / 미확인 {len(never_checked)} / 재확인대상 {len(stale)} / '
                           f'이번 처리 {len(pending)}')
        if not pending:
            self.stdout.write('처리할 항목 없음')
            return

        driver = dm.new_driver()
        fail_streak = 0
        done = 0
        try:
            dm.do_login(driver)
            for code in pending:
                # 중단 신호: 락 파일이 없어졌거나 다른 pid로 바뀌면 정지
                if not os.path.exists(LOCKFILE):
                    self.stdout.write('중단 신호 감지 — 종료')
                    break
                r = dm.check_code(driver, code)
                status = dm.result_to_status(r)
                if status is None:
                    fail_streak += 1
                else:
                    fail_streak = 0
                    LCodeStatus.objects.update_or_create(
                        l_code=code, defaults={'status': status, 'checked_at': timezone.now()})
                done += 1
                if fail_streak >= 3:
                    self.stdout.write(self.style.ERROR('연속 3회 실패 — 중단'))
                    break
                if done % 25 == 0:
                    self.stdout.write(f'{done}/{len(pending)} 진행 중...')
                time.sleep(random.uniform(1.0, 2.0))
        finally:
            driver.quit()

        self.stdout.write(self.style.SUCCESS(f'완료: {done}/{len(pending)} 처리'))
