"""11번가 계정별 '시간별' CPC 광고비 → 텔레그램. 오늘누적 + 직전 1시간 증가분.

형식:  rejoice666  CPC 15,000(+6,200)
거래원장(ElevenCostHistory, transaction_type='CPC')만 읽음(크롤 없음).
11번가 광고비는 CPC만(AI매출업은 지마켓 전용). 저녁 시간당 cron에서 호출.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '11번가 계정별 시간별 CPC 광고비 증가분 텔레그램 알림'

    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*', help='특정 seller_id 만')
        parser.add_argument('--window-min', type=int, default=70, help='증가분 집계 창(분), 기본 70')
        parser.add_argument('--no-telegram', action='store_true', help='발송 없이 출력만')
        parser.add_argument('--always', action='store_true', help='발생 없어도 발송(기본은 발생시만)')

    def handle(self, *args, **o):
        from datetime import timedelta
        from django.utils import timezone
        from django.db.models import Sum
        from apps.cpc.models import ElevenCostHistory, CrawlerAccount
        from apps.cpc import eleven_block_guard as guard

        now = timezone.localtime()
        day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        win = now - timedelta(minutes=o['window_min'])

        accts = CrawlerAccount.objects.filter(platform='11st', is_active=True)
        if o.get('accounts'):
            accts = accts.filter(login_id__in=o['accounts'])
        ids = list(accts.values_list('login_id', flat=True))

        def grouped(since):
            q = (ElevenCostHistory.objects
                 .filter(transaction_type='CPC', transaction_datetime__gte=since, seller_id__in=ids)
                 .values('seller_id').annotate(s=Sum('amount')))
            return {r['seller_id']: abs(r['s'] or 0) for r in q}

        day_map = grouped(day)
        win_map = grouped(win)

        # 전체금액(모든 계정 오늘 누적/직전1h 증가) 합계
        tot_c = sum(day_map.values())
        tot_d = sum(win_map.values())
        # 표시는 직전 1시간 증가분이 있는 계정만
        rows = [(day_map.get(sid, 0), sid, win_map.get(sid, 0))
                for sid in set(day_map) | set(win_map) if win_map.get(sid, 0) > 0]
        rows.sort(key=lambda r: -r[2])   # 증가분 큰 순

        def sd(v):
            return f'+{v:,}' if v > 0 else '+0'

        if not rows and not o.get('always'):
            self.stdout.write('11번가 CPC 증가 없음 — 미발송')
            return

        head = f"📊 [11번가 시간별 CPC광고비] {now.strftime('%m/%d %H:%M')}"
        total = f"💰 오늘 전체 CPC 광고비 {tot_c:,}원({sd(tot_d)})  · 증가 {len(rows)}계정"
        lines = [f"{sid}  CPC {cur:,}({sd(d)})" for cur, sid, d in rows]
        body = head + "\n" + total + ("\n" + "\n".join(lines) if lines else "")

        if not o.get('no_telegram'):
            try:
                guard._send_telegram_alert(body)
            except Exception as e:
                self.stderr.write(f'텔레그램 발송 실패: {e}')
        self.stdout.write(body)
