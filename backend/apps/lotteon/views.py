import datetime

from django.db.models import Sum, Count, Max, Q
from rest_framework import views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.lotteon.models import LotteonAccount, LotteonAdCost, LotteonMyProduct
from apps.sales.models import SalesRecord

LOTTEON_STATUS_MAP = {'SALE': '판매중', 'END': '판매종료', 'SOUT': '품절', 'STP': '판매중지'}
LOTTEON_STATUS_REVERSE = {v: k for k, v in LOTTEON_STATUS_MAP.items()}


class LotteonAccountsView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        accounts = LotteonAccount.objects.filter(is_active=True).annotate(
            product_count=Count('products')
        ).order_by('display_order', 'id')
        return Response([{
            'id': a.id,
            'login_id': a.login_id,
            'store_name': a.store_name,
            'seller_no': a.seller_no,
            'has_api_key': a.has_api_key,
            'product_count': a.product_count,
        } for a in accounts])


class LotteonMyProductListView(views.APIView):
    """롯데온 나의 상품 조회 — 나의상품 통합뷰(/myproduct) 플랫폼별 선택 조회용."""
    permission_classes = [IsAuthenticated]

    _SORT = {'product_name': 'product_name', 'sale_price': 'sale_price', 'stock_quantity': 'id',
             'status_type': 'status_code', 'seller_product_code': 'seller_product_code',
             'login_id': 'account__login_id', 'seller_name': 'account__store_name', 'synced_at': 'synced_at'}

    def get(self, request):
        account_id = request.query_params.get('account_id')
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 50))
        status_q = request.query_params.get('status') or None
        search = request.query_params.get('search') or None
        sort = request.query_params.get('sort') or 'synced_at'
        order = request.query_params.get('order') or 'desc'

        qs = LotteonMyProduct.objects.select_related('account')
        if account_id:
            qs = qs.filter(account_id=account_id)
        status_allowed = True
        if status_q:
            code = LOTTEON_STATUS_REVERSE.get(status_q)
            if code:
                qs = qs.filter(status_code=code)
            else:
                status_allowed = False
        if search:
            qs = qs.filter(Q(product_name__icontains=search) | Q(pd_no__icontains=search)
                            | Q(seller_product_code__icontains=search) | Q(account__login_id__icontains=search))

        f = self._SORT.get(sort, 'synced_at')
        qs = qs.order_by(('-' if order == 'desc' else '') + f, '-id')

        total = qs.count() if status_allowed else 0
        offset = (page - 1) * per_page
        rows = qs[offset:offset + per_page] if status_allowed else []

        items = [{
            'id': p.id, 'login_id': p.account.login_id, 'seller_name': p.account.store_name or p.account.login_id,
            'product_no': p.pd_no, 'product_name': p.product_name,
            'sale_price': p.sale_price, 'stock_quantity': None,
            'status_type': p.status_code, 'status_label': LOTTEON_STATUS_MAP.get(p.status_code, p.status_code),
            'seller_product_code': p.seller_product_code, 'category': p.category_path,
            'product_image_url': '',
            'synced_at': p.synced_at.isoformat() if p.synced_at else None,
        } for p in rows]

        return Response({
            'items': items, 'total': total, 'page': page, 'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page if total else 0,
        })


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
