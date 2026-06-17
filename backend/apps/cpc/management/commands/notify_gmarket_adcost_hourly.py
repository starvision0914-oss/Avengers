"""지마켓 계정별 '시간별' 광고비 증가분 → 텔레그램.

직전 스냅샷(GmarketDepositSnapshot) 대비 CPC/AI 증가분 + 현재 누적을 계정별로 표시.
형식:  rejoice666  CPC 15,000(+6,200) / AI 8,000(+1,000)
crawl_gmarket_cost 직후 호출(09~19시 매시간 cron).
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '지마켓 계정별 시간별 광고비 증가분(CPC/AI) 텔레그램 알림'

    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*', help='특정 login_id 만')
        parser.add_argument('--no-telegram', action='store_true', help='발송 없이 출력만')

    def handle(self, *args, **o):
        from django.utils import timezone
        from apps.cpc.models import GmarketDepositSnapshot, CrawlerAccount
        from apps.cpc import eleven_block_guard as guard

        now = timezone.localtime()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True)
        if o.get('accounts'):
            qs = qs.filter(login_id__in=o['accounts'])
        # 공유ESM 서브 제외(대표만) — 서브는 대표 스냅샷에 합쳐져 있음
        accts = [a for a in qs.order_by('display_order', 'login_id')
                 if not (a.gmarket_origin_id and a.gmarket_origin_id != a.login_id)]

        rows = []
        tot = {'cpc': 0, 'cpc_d': 0, 'ai': 0, 'ai_d': 0}
        no_data = []
        for a in accts:
            snaps = list(GmarketDepositSnapshot.objects
                         .filter(gmarket_id=a.login_id, collected_at__gte=day_start)
                         .order_by('collected_at'))
            if not snaps:
                no_data.append(a.login_id)
                continue
            cur = snaps[-1]
            prev = snaps[-2] if len(snaps) >= 2 else None
            cpc_c = cur.gmarket_cpc + cur.auction_cpc
            ai_c = cur.ai_usage
            cpc_p = (prev.gmarket_cpc + prev.auction_cpc) if prev else 0
            ai_p = prev.ai_usage if prev else 0
            cpc_d, ai_d = cpc_c - cpc_p, ai_c - ai_p
            tot['cpc'] += cpc_c; tot['cpc_d'] += cpc_d
            tot['ai'] += ai_c; tot['ai_d'] += ai_d
            rows.append((cpc_c + ai_c, a.login_id, cpc_c, cpc_d, ai_c, ai_d))

        # 계정 번호(display_order) 순 유지 — accts를 이미 그 순서로 조회함.
        # (이전엔 금액순 rows.sort 로 번호가 뒤섞여 알림 순서가 안 맞았음)

        def sd(v):   # 증가분 표기: +n / -n / 0
            return f'+{v:,}' if v > 0 else (f'{v:,}' if v < 0 else '+0')

        lines = [f"{lid}  CPC {cpc_c:,}({sd(cpc_d)}) / AI {ai_c:,}({sd(ai_d)})"
                 for _, lid, cpc_c, cpc_d, ai_c, ai_d in rows]

        head = f"📊 [지마켓 시간별 광고비] {now.strftime('%m/%d %H:%M')}  현재(직전대비)"
        total = (f"합계  CPC {tot['cpc']:,}({sd(tot['cpc_d'])}) / "
                 f"AI {tot['ai']:,}({sd(tot['ai_d'])})  · {len(rows)}계정")
        body = head + "\n" + total + "\n" + "\n".join(lines)
        if no_data:
            body += f"\n(스냅샷없음 {len(no_data)}: {', '.join(no_data[:10])})"

        if not o.get('no_telegram'):
            try:
                guard._send_telegram_alert(body)
            except Exception as e:
                self.stderr.write(f'텔레그램 발송 실패: {e}')
        self.stdout.write(body)
