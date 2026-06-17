"""11번가 오늘 광고비 발생 여부를 체크해 텔레그램으로 알림.
크론에서 강제수집(crawl_11st_cost --force) 직후 호출해 당일 광고비 발생을 확정 통지."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '11번가 오늘 광고비(CPC) 발생 여부 체크 후 텔레그램 알림'

    def add_arguments(self, parser):
        parser.add_argument('--label', default='광고비 체크', help='알림 라벨(예: 17시 광고비 체크)')

    def handle(self, *args, **opts):
        from datetime import datetime, timedelta
        import pytz
        from django.db.models import Sum, Count
        from django.utils import timezone
        from apps.cpc.models import ElevenCostHistory
        from apps.cpc import eleven_block_guard as guard

        kst = pytz.timezone('Asia/Seoul')
        now = timezone.localtime()
        today = now.date()
        start = kst.localize(datetime.combine(today, datetime.min.time()))
        end = start + timedelta(days=1)

        q = ElevenCostHistory.objects.filter(
            transaction_datetime__gte=start, transaction_datetime__lt=end,
            transaction_type='CPC')
        agg = q.aggregate(s=Sum('amount'), n=Count('seller_id', distinct=True))
        total = abs(agg['s'] or 0)
        n = agg['n'] or 0
        last = q.aggregate(m=__import__('django').db.models.Max('transaction_datetime'))['m']
        last_str = timezone.localtime(last).strftime('%H:%M') if last else '-'

        if total > 0:
            status = f'✅ 광고비 발생 중 (최신 {last_str})'
        else:
            status = '⚠️ 광고비 미발생 — 확인 필요'

        msg = (f"🔔 [11번가 {opts['label']}] {now.strftime('%m/%d %H:%M')}\n"
               f"오늘 광고비: {total:,}원 ({n}계정)\n{status}")
        try:
            guard._send_telegram_alert(msg)
        except Exception as e:
            self.stderr.write(f'텔레그램 발송 실패: {e}')
        self.stdout.write(msg)
