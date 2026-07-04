import datetime

from django.db.models import Sum, Count, Max
from django.utils import timezone as dj_timezone
from rest_framework import views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.coupang.models import CoupangAccount, CoupangOrder, CoupangProduct, CoupangVatSales


class CoupangDashboardView(views.APIView):
    """쿠팡 계정별 요약 — 상품수/주문건수·금액/부가세신고매출."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_to:
            d1 = datetime.date.fromisoformat(date_to)
        else:
            d1 = datetime.date.today()
        if date_from:
            d0 = datetime.date.fromisoformat(date_from)
        else:
            d0 = d1.replace(day=1)

        accounts = list(CoupangAccount.objects.filter(is_active=True).order_by('display_order', 'id'))

        product_counts = {r['account_id']: r['n'] for r in (
            CoupangProduct.objects.values('account_id').annotate(n=Count('id')))}
        approved_counts = {r['account_id']: r['n'] for r in (
            CoupangProduct.objects.filter(status_name='승인완료').values('account_id').annotate(n=Count('id')))}
        rejected_counts = {r['account_id']: r['n'] for r in (
            CoupangProduct.objects.filter(status_name='승인반려').values('account_id').annotate(n=Count('id')))}

        # 타임존 함정: __date 조회는 USE_TZ 상태에서 0건 반환될 수 있어 KST 자정 기준 datetime 범위로 조회
        tz = dj_timezone.get_current_timezone()
        dt0 = dj_timezone.make_aware(datetime.datetime.combine(d0, datetime.time.min), tz)
        dt1 = dj_timezone.make_aware(datetime.datetime.combine(d1, datetime.time.max), tz)
        order_qs = CoupangOrder.objects.filter(ordered_at__gte=dt0, ordered_at__lte=dt1)
        order_agg = {r['account_id']: r for r in (
            order_qs.values('account_id').annotate(cnt=Count('id'), total=Sum('sales_price')))}

        vat_agg = {r['account_id']: r['s'] for r in (
            CoupangVatSales.objects.filter(year=d1.year).values('account_id').annotate(s=Sum('total_sales')))}

        last_sync = {r['account_id']: r['m'] for r in (
            CoupangOrder.objects.values('account_id').annotate(m=Max('collected_at')))}

        rows = []
        totals = {'product_count': 0, 'order_count': 0, 'order_total': 0, 'vat_total': 0}
        for i, acct in enumerate(accounts, start=1):
            o = order_agg.get(acct.id, {})
            row = {
                'no': i,
                'login_id': acct.login_id,
                'seller_name': acct.seller_name,
                'has_api_key': acct.has_api_key,
                'is_rocket_growth': acct.is_rocket_growth,
                'product_count': product_counts.get(acct.id, 0),
                'approved_count': approved_counts.get(acct.id, 0),
                'rejected_count': rejected_counts.get(acct.id, 0),
                'order_count': o.get('cnt', 0),
                'order_total': o.get('total', 0) or 0,
                'vat_total': vat_agg.get(acct.id, 0) or 0,
                'last_synced': last_sync.get(acct.id),
            }
            rows.append(row)
            totals['product_count'] += row['product_count']
            totals['order_count'] += row['order_count']
            totals['order_total'] += row['order_total']
            totals['vat_total'] += row['vat_total']

        return Response({
            'date_from': d0.isoformat(), 'date_to': d1.isoformat(),
            'totals': totals, 'rows': rows,
        })
