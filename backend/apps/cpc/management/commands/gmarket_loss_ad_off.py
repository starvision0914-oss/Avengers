"""지마켓 적자상품 광고 자동 OFF.
1단계(안전·기본): 적자상품 탐지 → OFF 대상 리스트 산출 + 텔레그램 알림. 광고 건드리지 않음(dry-run).
2단계(--real): 실제 광고센터 상품별 OFF — 안전상 UI 플로우 1상품 검증 전까지 차단(VERIFIED=False).

적자 기준(기본): 당월 CPC 광고비≥cost_min & 클릭≥clicks_min & (전환0 또는 ROAS≤roas_max).
예) python manage.py gmarket_loss_ad_off                 # dry-run(탐지+알림)
    python manage.py gmarket_loss_ad_off --no-telegram   # 알림 없이 리스트만
    python manage.py gmarket_loss_ad_off --real          # (차단됨) 실제 OFF
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


# 실제 광고센터 OFF 플로우(상품별)는 1상품 dry-run 검증 후 활성화. 그 전엔 real 차단.
REAL_OFF_VERIFIED = False


class Command(BaseCommand):
    help = '지마켓 적자상품 광고 OFF 대상 산출(+텔레그램). --real은 검증 후 활성.'

    def add_arguments(self, parser):
        parser.add_argument('--cost-min', type=int, default=2000)
        parser.add_argument('--clicks-min', type=int, default=10)
        parser.add_argument('--roas-max', type=float, default=100.0)
        parser.add_argument('--months', type=int, default=1,
                            help='집계 대상 개월 수(당월부터 역순). 기본 1=당월(OFF용 권장). 긴 기간은 누적분석용')
        parser.add_argument('--eid', default=None, help='특정 계정만')
        parser.add_argument('--no-telegram', action='store_true', help='텔레그램 알림 끄기')
        parser.add_argument('--real', action='store_true', help='실제 광고 OFF 실행(검증 후 활성)')

    def handle(self, *args, **o):
        from django.db.models import Sum, Q
        from apps.cpc.models import GmarketProductAdCost, GmarketMyProduct
        today = timezone.localdate()
        cmin, clkmin, rmax = o['cost_min'], o['clicks_min'], o['roas_max']

        # 집계 기간(당월부터 N개월 역순). OFF용 기본=당월(현재 낭비), 길게 잡으면 누적(분석용).
        nmonths = max(1, o['months'])
        yms, yy, mm = [], today.year, today.month
        for _ in range(nmonths):
            yms.append((yy, mm)); mm -= 1
            if mm == 0: mm, yy = 12, yy - 1
        pq = Q()
        for (y, m) in yms:
            pq |= Q(year=y, month=m)
        self._period_label = (f'당월({today.year}-{today.month:02d}, ~{today})' if nmonths == 1
                              else f'최근 {nmonths}개월 누적({yms[-1][0]}-{yms[-1][1]:02d}~{today.year}-{today.month:02d})')
        base = GmarketProductAdCost.objects.filter(ad_type='cpc').filter(pq)
        if o['eid']:
            base = base.filter(login_id=o['eid'])
        grp = (base.values('product_no', 'login_id')
               .annotate(c=Sum('cost'), v=Sum('conv_amount'), clk=Sum('clicks'))
               .filter(c__gte=cmin, clk__gte=clkmin))
        loss = []
        for g in grp:
            roas = (g['v'] or 0) * 100.0 / g['c'] if g['c'] else 0
            if (g['v'] or 0) == 0 or roas <= rmax:
                loss.append({'pno': g['product_no'], 'lid': g['login_id'],
                             'cost': g['c'] or 0, 'conv': g['v'] or 0, 'clk': g['clk'] or 0,
                             'roas': round(roas, 1)})
        loss.sort(key=lambda x: -x['cost'])
        # 판매자코드/상품명 매핑(표시용)
        pmap = {p['product_no']: (p['seller_product_code'], p['product_name'])
                for p in GmarketMyProduct.objects.filter(
                    product_no__in=[r['pno'] for r in loss]).values('product_no', 'seller_product_code', 'product_name')}
        waste = sum(r['cost'] for r in loss)
        by_acct = {}
        for r in loss:
            by_acct.setdefault(r['lid'], []).append(r['pno'])

        self.stdout.write(f'[적자 OFF 대상] 기간={self._period_label} · 기준 광고비≥{cmin}·클릭≥{clkmin}·ROAS≤{rmax}')
        self.stdout.write(f'  적자상품 {len(loss)}개 / 낭비 광고비 {waste:,}원 / {len(by_acct)}계정')
        for r in loss[:20]:
            sc, nm = pmap.get(r['pno'], ('', ''))
            self.stdout.write(f"  {r['lid']:12s} {r['pno']:12s} 광고비 {r['cost']:>7,} 클릭 {r['clk']:>3} ROAS {r['roas']:>5}%  {(nm or '')[:24]}")
        if len(loss) > 20:
            self.stdout.write(f'  ... 외 {len(loss)-20}개')

        # 텔레그램 알림
        if not o['no_telegram'] and loss:
            self._telegram(today, loss, waste, by_acct, pmap)

        # 실제 OFF
        if o['real']:
            if not REAL_OFF_VERIFIED:
                self.stdout.write(self.style.WARNING(
                    '\n⚠️ 실제 광고 OFF는 아직 비활성화 상태입니다. 광고센터 상품별 OFF UI 플로우를 '
                    '1상품 dry-run으로 검증한 뒤 REAL_OFF_VERIFIED=True로 활성화됩니다. '
                    '지금은 탐지+알림(dry-run)만 수행했습니다.'))
                return
            self._real_off(by_acct, pmap)

    def _telegram(self, day, loss, waste, by_acct, pmap):
        try:
            import requests
            from apps.cpc.models import TelegramConfig, TelegramRecipient
            cfg = TelegramConfig.objects.first()
            if not cfg or not cfg.bot_token:
                return
            lines = [f'🛑 *지마켓 적자상품 광고 OFF 권장*',
                     f'기준: {self._period_label}',
                     f'적자 {len(loss)}개 · 낭비 광고비 *{waste:,}원* · {len(by_acct)}계정', '']
            for r in loss[:10]:
                _, nm = pmap.get(r['pno'], ('', ''))
                lines.append(f"• {r['lid']} {r['pno']} 광고비{r['cost']:,} 클릭{r['clk']} ROAS{r['roas']}% {(nm or '')[:16]}")
            if len(loss) > 10:
                lines.append(f'… 외 {len(loss)-10}개')
            lines.append('\n→ 셀러오피스/광고센터에서 OFF 권장 (자동OFF 검증 후 활성화 예정)')
            text = '\n'.join(lines)
            url = f'https://api.telegram.org/bot{cfg.bot_token}/sendMessage'
            for rcp in TelegramRecipient.objects.filter(is_active=True):
                try:
                    requests.post(url, data={'chat_id': rcp.chat_id, 'text': text,
                                             'parse_mode': 'Markdown'}, timeout=15)
                except Exception:
                    pass
            self.stdout.write('  텔레그램 알림 전송됨')
        except Exception as e:
            self.stdout.write(f'  텔레그램 실패: {e}')

    def _real_off(self, by_acct, pmap):
        # 2단계: 광고센터 상품별 OFF (검증 후 구현 활성화)
        self.stdout.write('실제 OFF 실행 — (구현 예정: 광고센터 상품별 OFF 크롤러)')
