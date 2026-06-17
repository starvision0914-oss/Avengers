"""지마켓 광고 상시 진단 엔진 (읽기전용) — 상품을 효율 등급으로 분류하고 리포트.

분류(최근 N개월 광고비 기준):
  판매불가/삭제  : 카탈로그에서 빠짐(이미 광고 거의 멈춤) — 적자 오분류 방지용 분리
  무전환낭비     : 클릭>=기준 & 실매출=0  → 순낭비(자동OFF 1순위 후보)
  적자           : 실ROAS < 손익분기(원가기반, 없으면 기본선)
  회색           : 손익분기~ 그 2배
  승자           : 실ROAS >= 손익분기*1.2

원가: 11번가 ElevenMyProduct.purchase_cost를 판매자코드로 연결. 없으면 기본 마진 가정.
※ 읽기전용 — 광고 OFF 등 실제 액션은 별도 명령으로(단계적·검증 후).
"""
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db.models import Sum


class Command(BaseCommand):
    help = '지마켓 광고 효율 진단/분류 (읽기전용 리포트)'

    def add_arguments(self, parser):
        parser.add_argument('--months', type=int, default=2, help='최근 N개월 광고비 기준')
        parser.add_argument('--fee', type=float, default=0.12, help='플랫폼 수수료율')
        parser.add_argument('--default-margin', type=float, default=0.20, help='원가 없을 때 기본 마진율')
        parser.add_argument('--min-click', type=int, default=15, help='무전환낭비 판정 최소 클릭')
        parser.add_argument('--telegram', action='store_true', help='결과 텔레그램 발송')

    def handle(self, *args, **o):
        from apps.cpc.models import GmarketProductAdCost as G, GmarketMyProduct, ElevenMyProduct
        from apps.cpc.views import _gmarket_realsales

        today = date.today()
        y, m = today.year, today.month
        periods = []
        for i in range(o['months']):
            mm = m - i
            yy = y
            while mm <= 0:
                mm += 12; yy -= 1
            periods.append((yy, mm))
        # 기간 광고비 집계
        q = G.objects.none()
        from django.db.models import Q
        flt = Q()
        for (yy, mm) in periods:
            flt |= Q(year=yy, month=mm)
        ad = {}
        for r in G.objects.filter(flt).values('product_no').annotate(c=Sum('cost'), cv=Sum('conv_amount'), ck=Sum('clicks')):
            ad[str(r['product_no'])] = [r['c'] or 0, r['cv'] or 0, r['ck'] or 0]
        pnos = list(ad.keys())
        # 원가맵 + 판매가/코드/상태
        costmap = {}
        for r in ElevenMyProduct.objects.exclude(purchase_cost__isnull=True).exclude(purchase_cost=0).values('seller_product_code', 'purchase_cost'):
            costmap.setdefault(r['seller_product_code'], r['purchase_cost'])
        gp = {}
        for r in GmarketMyProduct.objects.filter(product_no__in=pnos).values('product_no', 'sale_price', 'seller_product_code', 'status_type'):
            gp.setdefault(str(r['product_no']), (r['sale_price'] or 0, r['seller_product_code'] or '', r['status_type'] or ''))
        # 실매출
        real = {}
        d0 = date(periods[-1][0], periods[-1][1], 1)
        B = 3000
        for i in range(0, len(pnos), B):
            chunk = pnos[i:i + B]
            _c, real_by, _s, _o = _gmarket_realsales(d0, today, chunk)
            real.update(real_by)

        fee = o['fee']; dm = o['default_margin']; minck = o['min_click']
        cls = {k: [0, 0] for k in ['판매불가/삭제', '무전환낭비', '적자', '회색', '승자', '기타']}
        for p, (c, cv, ck) in ad.items():
            if c <= 0:
                continue
            sp, code, st = gp.get(p, (0, '', ''))
            rv = real.get(p, 0)
            # 손익분기 ROAS
            cost = costmap.get(code)
            if sp > 0 and cost and cost < sp:
                margin = (sp * (1 - fee) - cost) / sp
            else:
                margin = dm
            be = 100.0 / margin if margin > 0 else 9999
            roas_real = rv * 100.0 / c
            if (p not in gp) or any(x in st for x in ['불가', '삭제', '중지', '종료']):
                k = '판매불가/삭제'
            elif rv == 0 and ck >= minck:
                k = '무전환낭비'
            elif roas_real < be:
                k = '적자'
            elif roas_real < be * 2:
                k = '회색'
            else:
                k = '승자'
            cls[k][0] += c; cls[k][1] += 1
        tot = sum(v[0] for v in cls.values()) or 1
        lines = ['📊 지마켓 광고 진단 (최근 %d개월, 실ROAS·원가기준)' % o['months'], '']
        for k in ['승자', '회색', '적자', '무전환낭비', '판매불가/삭제', '기타']:
            c, n = cls[k]
            lines.append('%-10s 광고비 %12s (%4.1f%%)  %d개' % (k, format(int(c), ','), c * 100.0 / tot, n))
        lines.append('')
        lines.append('총 광고비 %s원 / 분석상품 %d개' % (format(int(tot), ','), len(ad)))
        cut = cls['무전환낭비'][0] + cls['적자'][0]
        lines.append('→ 컷 후보(적자+무전환) 광고비 %s원 (%.0f%%)' % (format(int(cut), ','), cut * 100.0 / tot))
        out = '\n'.join(lines)
        self.stdout.write(out)

        if o['telegram']:
            import requests
            from apps.cpc.models import TelegramConfig, TelegramRecipient
            cfg = TelegramConfig.objects.first()
            if cfg and cfg.bot_token:
                url = f'https://api.telegram.org/bot{cfg.bot_token}/sendMessage'
                for rcp in TelegramRecipient.objects.all():
                    try:
                        requests.post(url, data={'chat_id': rcp.chat_id, 'text': out}, timeout=15)
                    except Exception:
                        pass
