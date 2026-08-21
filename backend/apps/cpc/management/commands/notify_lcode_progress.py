"""도매마트 L코드 판매중/품절 조회 진행상황 → 텔레그램 (사용자 요청, 1시간마다)."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'L코드(도매마트) 조회 진행상황 텔레그램 알림'

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

        body = (
            f"🛒 [L코드 조회 진행상황]\n"
            f"{'실행 중' if running else '⛔ 중지됨'} · {checked:,}/{total:,}건 ({pct}%)\n"
            f"판매중 {counts['in_stock']:,} · 품절 {counts['soldout']:,} · 미확인 {counts['not_found']:,}"
        )
        try:
            guard._send_telegram_alert(body)
        except Exception as e:
            self.stderr.write(f'텔레그램 발송 실패: {e}')
        self.stdout.write(body)
