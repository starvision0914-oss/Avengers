import datetime

from django.db.models import Sum, Count, Max
from rest_framework import views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.lotteon.models import LotteonAccount, LotteonAdCost
from apps.sales.models import SalesRecord


class LotteonAccountsView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        accounts = LotteonAccount.objects.filter(is_active=True).order_by('display_order', 'id')
        return Response([{
            'id': a.id,
            'login_id': a.login_id,
            'store_name': a.store_name,
            'seller_no': a.seller_no,
            'has_api_key': a.has_api_key,
        } for a in accounts])


class LotteonDashboardView(views.APIView):
    """롯데온 계정별 요약 — 매출/구매가(엑셀업로드 SalesRecord)+광고비(LotteonAdCost)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start = request.query_params.get('start')
        end = request.query_params.get('end')
        if not start or not end:
            today = datetime.date.today()
            end = today - datetime.timedelta(days=1)
            start = end.replace(day=1)
        else:
            start = datetime.date.fromisoformat(start)
            end = datetime.date.fromisoformat(end)

        accounts = list(LotteonAccount.objects.filter(is_active=True).order_by('display_order', 'id'))
        login_to_acc = {a.login_id: a for a in accounts}

        # 매출/구매가: apps/sales 범용 엑셀업로드로 들어온 SalesRecord (platform='lotteon')
        sr_qs = SalesRecord.objects.filter(
            platform='lotteon', order_date__gte=start, order_date__lte=end,
        )
        sales_agg = {}
        for r in sr_qs.values('seller__seller_id').annotate(
            sales=Sum('total_price'), cogs=Sum('cost'), commission=Sum('commission'), orders=Count('id'),
        ):
            sid = r['seller__seller_id']
            acc = login_to_acc.get(sid)
            if acc:
                sales_agg[acc.id] = r

        # 광고비: LotteonAdCost (아직 크롤러 미구현이면 전부 0)
        ad_qs = LotteonAdCost.objects.filter(date__gte=start, date__lte=end)
        ad_agg = {r['account_id']: r['c'] for r in (
            ad_qs.values('account_id').annotate(c=Sum('cost')))}

        last_sync = {a.id: a.last_crawled_at for a in accounts}

        rows = []
        totals = {'sales': 0, 'cogs': 0, 'ad_cost': 0, 'orders': 0, 'net': 0}
        for i, acct in enumerate(accounts, start=1):
            s = sales_agg.get(acct.id, {})
            sales = s.get('sales') or 0
            cogs = s.get('cogs') or 0
            ad_cost = ad_agg.get(acct.id, 0) or 0
            orders = s.get('orders') or 0
            net = sales - cogs - ad_cost
            row = {
                'no': i,
                'account_id': acct.id,
                'login_id': acct.login_id,
                'store_name': acct.store_name or acct.login_id,
                'seller_no': acct.seller_no,
                'has_api_key': acct.has_api_key,
                'sales': sales,
                'cogs': cogs,
                'ad_cost': ad_cost,
                'orders': orders,
                'net': net,
                'roas': round(sales / ad_cost * 100, 1) if ad_cost > 0 else None,
                'last_synced': last_sync.get(acct.id),
            }
            rows.append(row)
            totals['sales'] += sales
            totals['cogs'] += cogs
            totals['ad_cost'] += ad_cost
            totals['orders'] += orders
            totals['net'] += net

        return Response({
            'start': start.isoformat(), 'end': end.isoformat(),
            'totals': totals, 'rows': rows,
        })
