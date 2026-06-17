"""지마켓 오늘 광고비(특히 17시 이후 발생분)를 체크해 텔레그램으로 알림.
크론에서 오늘치 강제수집(orch_today.sh) 직후 호출 → 17시 이후 발생 광고비가 있으면 통지.
거래원장 GmarketCostHistory의 traded_at(거래시각) 기준."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '지마켓 오늘 광고비 17시 이후 발생분 체크 후 텔레그램 알림'

    def add_arguments(self, parser):
        parser.add_argument('--label', default='17시 광고비 체크', help='알림 라벨')
        parser.add_argument('--since-hour', type=int, default=17, help='기준 시각(시), 기본 17')

    def handle(self, *args, **opts):
        from datetime import datetime, timedelta
        import pytz
        from django.db.models import Sum, Count, Max
        from django.utils import timezone
        from apps.cpc.models import GmarketCostHistory, CrawlerAccount
        from apps.cpc import eleven_block_guard as guard

        kst = pytz.timezone('Asia/Seoul')
        now = timezone.localtime()
        today = now.date()
        since_h = opts['since_hour']
        AD = ['CPC', 'AI매출업', '서버비용']

        # 오늘 전체(거래원장, market=gmarket+auction 합산)
        day_qs = GmarketCostHistory.objects.filter(
            use_date=today, transaction_type__in=AD)
        day_total = abs(day_qs.aggregate(s=Sum('amount'))['s'] or 0)

        # 17시 이후 발생분 — traded_at의 KST 시각이 since_h시 이후
        since_dt = kst.localize(datetime.combine(today, datetime.min.time())) + timedelta(hours=since_h)
        end_dt = kst.localize(datetime.combine(today, datetime.min.time())) + timedelta(days=1)
        after_qs = day_qs.filter(traded_at__gte=since_dt, traded_at__lt=end_dt)
        after_total = abs(after_qs.aggregate(s=Sum('amount'))['s'] or 0)
        after_cnt = after_qs.count()
        n_acct = after_qs.values('seller_id').distinct().count()
        last = after_qs.aggregate(m=Max('traded_at'))['m']
        last_str = timezone.localtime(last).strftime('%H:%M') if last else '-'

        # 계정별 17시 이후 발생액 — 계정 번호(display_order) 순으로 정렬(거래내역엔 번호 없어 매핑)
        order_map = {a.login_id: (a.display_order, a.login_id)
                     for a in CrawlerAccount.objects.filter(platform='gmarket')}
        agg = list(after_qs.values('seller_id').annotate(s=Sum('amount'), n=Count('id')))
        agg.sort(key=lambda r: order_map.get(r['seller_id'], (99999, r['seller_id'])))
        tops = [f"  · {r['seller_id']}: {abs(r['s']):,}원 ({r['n']}건)" for r in agg[:12]]

        if after_total > 0:
            head = f"🔔 [지마켓 {opts['label']}] {now.strftime('%m/%d %H:%M')}"
            body = (f"\n⚠️ {since_h}시 이후 광고비 발생: {after_total:,}원 ({n_acct}계정/{after_cnt}건, 최신 {last_str})"
                    f"\n오늘 총 광고비: {day_total:,}원")
            if tops:
                body += "\n[계정별 17시↑]\n" + "\n".join(tops)
            msg = head + body
        else:
            msg = (f"🔕 [지마켓 {opts['label']}] {now.strftime('%m/%d %H:%M')}"
                   f"\n{since_h}시 이후 광고비 없음. 오늘 총 광고비: {day_total:,}원")

        try:
            guard._send_telegram_alert(msg)
        except Exception as e:
            self.stderr.write(f'텔레그램 발송 실패: {e}')
        self.stdout.write(msg)
