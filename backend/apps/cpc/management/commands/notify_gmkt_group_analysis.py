"""지마켓 그룹(eid) 상태반영 분석 → 텔레그램.
ROAS≥200 키워드 수집현황 + 적자상품(삭제대기) 요약. 공유ESM 그룹은 마스터 eid로 집계됨.
예: python manage.py notify_gmkt_group_analysis --eid dlwodb000
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '지마켓 그룹 상태반영 분석(적자 삭제대기 + ROAS≥200 키워드 수집현황) → 텔레그램'

    def add_arguments(self, parser):
        parser.add_argument('--eid', default='dlwodb000', help='대상 마스터 login_id')
        parser.add_argument('--cost-min', type=int, default=2000)
        parser.add_argument('--roas-max', type=float, default=100)
        parser.add_argument('--clicks-min', type=int, default=10)
        parser.add_argument('--no-telegram', action='store_true')

    def handle(self, *args, **o):
        from django.db.models import Sum, Max
        from apps.cpc.models import (GmarketProductAdCost, GmarketKeywordReport,
                                     GmarketLossDeleted, GmarketMyProduct)
        eid = o['eid']; cmin = o['cost_min']; rmax = o['roas_max']; clkmin = o['clicks_min']

        synced = GmarketMyProduct.objects.filter(account__login_id=eid).aggregate(m=Max('synced_at'))['m']
        synced_s = synced.astimezone().strftime('%m-%d %H:%M') if synced else '없음'

        grp = list(GmarketProductAdCost.objects.filter(login_id=eid).values('product_no')
                   .annotate(cost=Sum('cost'), conv=Sum('conv_amount'), clk=Sum('clicks')))

        def roas(g):
            return (g['conv'] * 100.0 / g['cost']) if g['cost'] else 0
        roas200 = {g['product_no'] for g in grp if g['cost'] and roas(g) >= 200}
        loss = [g for g in grp if g['cost'] and g['cost'] >= cmin and (g['clk'] or 0) >= clkmin and roas(g) <= rmax]
        waste = sum(g['cost'] for g in loss)

        kw_pnos = set(GmarketKeywordReport.objects.filter(login_id=eid).values_list('product_no', flat=True))
        kw_done = len(roas200 & kw_pnos)
        kw_todo = len(roas200) - kw_done
        deleted = GmarketLossDeleted.objects.filter(login_id=eid).count()

        # 적자상품의 판매상태 분포 (03시 크롤로 갱신된 status 반영)
        loss_pnos = [g['product_no'] for g in loss]
        st = {'판매중': 0, '판매중지': 0, '삭제/불가': 0, '기타': 0}
        if loss_pnos:
            stat_map = {}
            for r in (GmarketMyProduct.objects.filter(product_no__in=loss_pnos)
                      .order_by('-synced_at').values('product_no', 'status_type')):
                stat_map.setdefault(r['product_no'], r['status_type'] or '')
            for p in loss_pnos:
                s = stat_map.get(p, '')
                if s == '판매중':
                    st['판매중'] += 1
                elif s in ('판매중지', '품절', '판매종료'):
                    st['판매중지'] += 1
                elif s in ('삭제', '판매불가') or p not in stat_map:
                    st['삭제/불가'] += 1
                else:
                    st['기타'] += 1

        lines = [
            f'📊 지마켓 *{eid}* 상태반영 분석',
            f'판매상태 수집: {synced_s}',
            '',
            f'🔑 ROAS≥200 상품 *{len(roas200)}개*',
            f'  └ 키워드 수집 {kw_done}개 / 미수집 {kw_todo}개',
            '',
            f'🛑 적자상품(삭제대기) *{len(loss)}개* (광고비≥{cmin:,}·클릭≥{clkmin}·ROAS≤{int(rmax)})',
            f'  └ 낭비 광고비 *{waste:,}원* / 이미 삭제완료 {deleted}개',
            f'  └ 판매상태: 판매중 {st["판매중"]} · 판매중지 {st["판매중지"]} · 삭제/불가 {st["삭제/불가"]}'
            + (f' · 기타 {st["기타"]}' if st['기타'] else ''),
        ]
        text = '\n'.join(lines)
        self.stdout.write(text)

        if o['no_telegram']:
            return
        try:
            import requests
            from apps.cpc.models import TelegramConfig, TelegramRecipient
            cfg = TelegramConfig.objects.first()
            if not cfg or not cfg.bot_token:
                self.stdout.write('텔레그램 미설정 — 전송 생략')
                return
            url = f'https://api.telegram.org/bot{cfg.bot_token}/sendMessage'
            sent = 0
            for rcp in TelegramRecipient.objects.filter(is_active=True):
                try:
                    requests.post(url, data={'chat_id': rcp.chat_id, 'text': text,
                                             'parse_mode': 'Markdown'}, timeout=15)
                    sent += 1
                except Exception:
                    pass
            self.stdout.write(f'텔레그램 전송 {sent}건')
        except Exception as e:
            self.stdout.write(f'텔레그램 실패: {e}')
