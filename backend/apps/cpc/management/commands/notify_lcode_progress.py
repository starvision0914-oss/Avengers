"""도매마트 L코드 판매중/품절 조회 진행상황 → 텔레그램 (사용자 요청, 1시간마다).
중지 상태를 그냥 보고만 하면 아무도 안 눌러줄 때 계속 멈춰있게 된다(2026-08-22 9시간 방치 실측)
— 중지 감지 시 알림과 함께 자동으로 재개시킨다."""
import subprocess
from django.core.management.base import BaseCommand


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
        total = len(all_codes)
        counts = {'in_stock': 0, 'soldout': 0, 'not_found': 0}
        checked = 0
        for row in LCodeStatus.objects.filter(l_code__in=all_codes).values('status'):
            checked += 1
            if row['status'] in counts:
                counts[row['status']] += 1
        _, running = _crawl_lock_busy(LCODE_LOCKFILE)
        pct = round(checked / total * 100, 1) if total else 0

        resumed = False
        if not running and checked < total:
            try:
                subprocess.Popen(
                    ['python3', 'manage.py', 'check_domemart_lcodes'],
                    stdout=open('/tmp/check_domemart_lcodes.log', 'a'),
                    stderr=subprocess.STDOUT, start_new_session=True)
                resumed = True
            except Exception as e:
                self.stderr.write(f'자동재개 실패: {e}')

        status_line = '실행 중' if running else ('⛔ 중지 감지 → 자동 재개함' if resumed else '⛔ 중지됨(재개 실패)')
        body = (
            f"🛒 [L코드 조회 진행상황]\n"
            f"{status_line} · {checked:,}/{total:,}건 ({pct}%)\n"
            f"판매중 {counts['in_stock']:,} · 품절 {counts['soldout']:,} · 미확인 {counts['not_found']:,}"
        )
        # watchdog(10분 주기)는 정상 실행 중일 땐 조용히 넘어가고, 재개시켰거나 완전 완료됐을 때만 알림
        skip_alert = opts.get('watchdog') and running
        if not skip_alert:
            try:
                guard._send_telegram_alert(body)
            except Exception as e:
                self.stderr.write(f'텔레그램 발송 실패: {e}')
        self.stdout.write(body)
