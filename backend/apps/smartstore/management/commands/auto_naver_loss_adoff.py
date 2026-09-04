"""네이버 상품별 ROAS 기준 적자상품 자동 광고 OFF — 실매출(정산) 기준으로 판정.
광고센터 전환매출이 아니라 SmartStoreProduct 매핑 + SalesRecord(실매출)로 ROAS를 계산해
오탐(자연유입/직접구매로 실제론 흑자인데 광고센터엔 안 잡히는 경우)을 방지한다.
NaverProductRoasView/NaverRoasBulkAdOffView(수동 화면)와 동일 원칙·동일 임계값.

사용법:
  python manage.py auto_naver_loss_adoff              # 이번달, 기본 임계값
  python manage.py auto_naver_loss_adoff --dry-run     # 대상만 보고 실제 OFF 안 함
"""
import calendar
import datetime

from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone


class Command(BaseCommand):
    help = '네이버 실매출 기준 적자상품 자동 광고 OFF'

    def add_arguments(self, parser):
        parser.add_argument('--cost-min', type=int, default=2000)
        parser.add_argument('--roas-max', type=float, default=100)
        parser.add_argument('--clicks-min', type=int, default=10)
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--ym-from', default=None, help='기본=이번달 1일 (예: 2026-01, 소급 정리용)')
        parser.add_argument('--ym-to', default=None, help='기본=어제(이번달) (예: 2026-09)')

    def handle(self, *args, **opts):
        from apps.smartstore.models import NaverAdProductReport, SmartStoreProduct, SmartStoreAccount
        from apps.sales.models import SalesRecord
        from apps.cpc.views import _bare_seller_code
        from apps.smartstore.services.naver_search_ad import lock_ads_for_products

        today = timezone.localdate()
        if opts['ym_from']:
            y0, m0 = map(int, opts['ym_from'].split('-'))
            d0 = datetime.date(y0, m0, 1)
        else:
            d0 = today.replace(day=1)
        if opts['ym_to']:
            y1, m1 = map(int, opts['ym_to'].split('-'))
            d1 = datetime.date(y1, m1, calendar.monthrange(y1, m1)[1])
        else:
            d1 = today - datetime.timedelta(days=1) if today.day > 1 else today

        qs = NaverAdProductReport.objects.filter(since_date__gte=d0, since_date__lte=d1)
        agg = list(qs.values('account_id', 'product_no', 'product_name').annotate(
            total_cost=Sum('cost'), total_click=Sum('click'), total_conv_amt=Sum('conversion_amount'),
        ))
        pnos = {r['product_no'] for r in agg}
        prod_qs = SmartStoreProduct.objects.filter(channel_product_no__in=pnos).only(
            'account_id', 'channel_product_no', 'seller_management_code')
        prod_by_key = {(p.account_id, p.channel_product_no): p for p in prod_qs}
        acc_map = {a.id: (a.display_name or a.store_name) for a in SmartStoreAccount.objects.all()}

        codes = set()
        for p in prod_by_key.values():
            if p.seller_management_code:
                codes.add(p.seller_management_code)
                codes.add(_bare_seller_code(p.seller_management_code))
        sales_by_code = {}
        if codes:
            d_from = d0 - datetime.timedelta(days=45)
            for s in (SalesRecord.objects.filter(platform='smartstore', product_code__in=list(codes),
                                                 order_date__gte=d_from, order_date__lte=d1)
                      .values('product_code').annotate(s=Sum('total_price'))):
                sales_by_code[s['product_code']] = s['s'] or 0

        cost_min = opts['cost_min']; roas_max = opts['roas_max']; clicks_min = opts['clicks_min']
        targets_by_account = {}
        target_rows = []
        for r in agg:
            cost = r['total_cost'] or 0
            click = r['total_click'] or 0
            if cost < cost_min or click < clicks_min:
                continue
            # 광고센터 기준 ROAS(전환매출 기반) — 사용자 지시(2026-09-04): 실매출 기준 하나만으로는
            # 부족, 광고센터 기준도 같이 적자여야(AND) 광고 OFF 대상으로 삼는다. 둘 중 하나라도
            # 흑자면 보류(과도한 OFF로 인한 매출 기회손실 방지).
            conv_amt = r['total_conv_amt'] or 0
            ad_roas = round(conv_amt * 100.0 / cost, 1) if cost else 0
            p = prod_by_key.get((r['account_id'], r['product_no']))
            if not p or not p.seller_management_code:
                continue  # 실매출 근거 없으면 적자로 단정하지 않음
            sc = p.seller_management_code
            real_sales = sum(sales_by_code.get(x, 0) for x in {sc, _bare_seller_code(sc)})
            real_roas = round(real_sales * 100.0 / cost, 1) if cost else 0
            # 사용자 지시(2026-09-04, 밀양사과 케이스): 광고센터 ROAS가 아무리 높아도(=흑자로
            # 보여도) 정산 실매출이 완전히 0원이면 그 전환은 허수일 가능성이 높다 — 광고비·클릭이
            # 이미 충분한데 실매출이 단 1원도 없으면 광고센터 ROAS와 무관하게 OFF 대상으로 본다.
            if real_sales != 0 and ad_roas > roas_max:
                continue
            if real_roas > roas_max:
                continue
            targets_by_account.setdefault(r['account_id'], set()).add(r['product_no'])
            target_rows.append((acc_map.get(r['account_id'], ''), r['product_name'], cost, conv_amt, ad_roas, real_sales, real_roas))

        total_targets = sum(len(v) for v in targets_by_account.values())
        self.stdout.write(f'대상: {total_targets}개 상품 / {len(targets_by_account)}개 계정 '
                           f'(기준: 광고센터ROAS≤{roas_max}% AND 실매출ROAS≤{roas_max}% · 광고비≥{cost_min} · 클릭≥{clicks_min})')
        for name, pname, cost, conv_amt, ad_roas, sales, roas in target_rows[:30]:
            self.stdout.write(f'  {name} | {pname[:30]} | 광고비{cost:,} 광고센터매출{conv_amt:,}({ad_roas}%) 실매출{sales:,}({roas}%)')

        if opts['dry_run'] or not total_targets:
            return

        off_count = fail_count = 0
        for account_id, pnos in targets_by_account.items():
            account = SmartStoreAccount.objects.filter(id=account_id).first()
            if not account:
                continue
            for cust, lic, sec in [
                (account.naver_ad_customer_id, account.naver_ad_access_license, account.naver_ad_secret_key),
                (account.naver_ad_ai_customer_id, account.naver_ad_ai_access_license, account.naver_ad_ai_secret_key),
            ]:
                if not (cust and lic and sec):
                    continue
                for res in lock_ads_for_products(cust, lic, sec, pnos, lock=True):
                    if res['ok']:
                        off_count += 1
                    else:
                        fail_count += 1

        msg = f'📴 [네이버 실매출 적자상품 자동 광고OFF] {total_targets}개 대상 / {off_count}개 소재 OFF'
        if fail_count:
            msg += f' / {fail_count}개 실패'
        self.stdout.write(msg)
        try:
            from apps.cpc import eleven_block_guard as guard
            guard._send_telegram_alert(msg)
        except Exception as e:
            self.stderr.write(f'텔레그램 발송 실패: {e}')
