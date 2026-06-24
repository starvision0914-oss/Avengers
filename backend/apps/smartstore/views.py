import datetime
from django.db.models import Sum, Q
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import SmartStoreAccount, SmartStoreSales, SmartStoreAdCost, SmartStoreCrawlLog


# ──── 계정 ────

class AccountListView(APIView):
    def get(self, request):
        accounts = SmartStoreAccount.objects.filter(is_active=True).order_by('display_order')
        data = []
        for a in accounts:
            data.append({
                'id': a.id,
                'login_id': a.login_id,
                'store_name': a.store_name,
                'store_slug': a.store_slug,
                'display_name': a.display_name or a.store_name,
                'memo': a.memo,
                'has_pw': bool(a.login_pw),
                'is_active': a.is_active,
                'display_order': a.display_order,
            })
        return Response(data)

    def post(self, request):
        d = request.data
        obj = SmartStoreAccount.objects.create(
            login_id=d['login_id'],
            login_pw=d.get('login_pw', ''),
            store_name=d['store_name'],
            store_slug=d.get('store_slug', ''),
            display_name=d.get('display_name', ''),
            memo=d.get('memo', ''),
            display_order=d.get('display_order', 99),
        )
        return Response({'id': obj.id, 'store_name': obj.store_name}, status=201)


class AccountDetailView(APIView):
    def patch(self, request, pk):
        try:
            obj = SmartStoreAccount.objects.get(pk=pk)
        except SmartStoreAccount.DoesNotExist:
            return Response({'error': 'not found'}, status=404)

        d = request.data
        for field in ('login_id', 'login_pw', 'store_name', 'store_slug',
                      'display_name', 'memo', 'is_active', 'display_order'):
            if field in d:
                setattr(obj, field, d[field])
        obj.save()
        return Response({'ok': True})

    def delete(self, request, pk):
        SmartStoreAccount.objects.filter(pk=pk).update(is_active=False)
        return Response({'ok': True})


# ──── 대시보드 통계 ────

class DashboardView(APIView):
    def get(self, request):
        start = request.query_params.get('start')
        end = request.query_params.get('end')
        account_ids = request.query_params.getlist('account_id')

        if not start or not end:
            today = datetime.date.today()
            end = today - datetime.timedelta(days=1)
            start = today.replace(day=1)
        else:
            start = datetime.date.fromisoformat(start)
            end = datetime.date.fromisoformat(end)

        sales_qs = SmartStoreSales.objects.filter(date__gte=start, date__lte=end)
        ad_qs = SmartStoreAdCost.objects.filter(date__gte=start, date__lte=end)

        if account_ids:
            sales_qs = sales_qs.filter(account_id__in=account_ids)
            ad_qs = ad_qs.filter(account_id__in=account_ids)

        sales_agg = sales_qs.aggregate(
            total_sales=Sum('sales_amount'),
            total_cancel=Sum('cancel_amount'),
            total_return=Sum('return_amount'),
            total_settlement=Sum('settlement_amount'),
            total_orders=Sum('order_count'),
            total_commission=Sum('commission_amount'),
        )
        ad_agg = ad_qs.aggregate(
            total_ad_cost=Sum('cost'),
            total_clicks=Sum('click'),
            total_impressions=Sum('impression'),
            total_conversion=Sum('conversion_amount'),
        )

        total_sales = sales_agg['total_sales'] or 0
        total_settlement = sales_agg['total_settlement'] or 0
        total_ad = ad_agg['total_ad_cost'] or 0
        roas = round(total_settlement / total_ad * 100, 1) if total_ad > 0 else None

        # 계정별 합산
        by_account = {}
        for row in sales_qs.values('account_id').annotate(
            sales=Sum('sales_amount'),
            settlement=Sum('settlement_amount'),
            orders=Sum('order_count'),
        ):
            aid = row['account_id']
            by_account[aid] = {
                'sales': row['sales'] or 0,
                'settlement': row['settlement'] or 0,
                'orders': row['orders'] or 0,
                'ad_cost': 0,
            }

        for row in ad_qs.values('account_id').annotate(cost=Sum('cost')):
            aid = row['account_id']
            if aid not in by_account:
                by_account[aid] = {'sales': 0, 'settlement': 0, 'orders': 0, 'ad_cost': 0}
            by_account[aid]['ad_cost'] = row['cost'] or 0

        # 계정명 매핑
        accounts = {a.id: a.display_name or a.store_name
                    for a in SmartStoreAccount.objects.filter(is_active=True)}
        account_list = []
        for aid, row in by_account.items():
            s = row['settlement']
            c = row['ad_cost']
            account_list.append({
                'account_id': aid,
                'account_name': accounts.get(aid, str(aid)),
                **row,
                'roas': round(s / c * 100, 1) if c > 0 else None,
            })
        account_list.sort(key=lambda x: x['settlement'], reverse=True)

        # 일별 추이
        daily = []
        sales_by_date = {}
        for row in sales_qs.values('date').annotate(
            sales=Sum('sales_amount'),
            settlement=Sum('settlement_amount'),
            orders=Sum('order_count'),
        ).order_by('date'):
            sales_by_date[str(row['date'])] = {
                'date': str(row['date']),
                'sales': row['sales'] or 0,
                'settlement': row['settlement'] or 0,
                'orders': row['orders'] or 0,
                'ad_cost': 0,
            }

        for row in ad_qs.values('date').annotate(cost=Sum('cost')).order_by('date'):
            d = str(row['date'])
            if d not in sales_by_date:
                sales_by_date[d] = {'date': d, 'sales': 0, 'settlement': 0, 'orders': 0, 'ad_cost': 0}
            sales_by_date[d]['ad_cost'] = row['cost'] or 0

        daily = sorted(sales_by_date.values(), key=lambda x: x['date'])

        return Response({
            'period': {'start': str(start), 'end': str(end)},
            'summary': {
                'total_sales': total_sales,
                'total_cancel': sales_agg['total_cancel'] or 0,
                'total_return': sales_agg['total_return'] or 0,
                'total_settlement': total_settlement,
                'total_orders': sales_agg['total_orders'] or 0,
                'total_ad_cost': total_ad,
                'total_clicks': ad_agg['total_clicks'] or 0,
                'total_conversion': ad_agg['total_conversion'] or 0,
                'roas': roas,
            },
            'by_account': account_list,
            'daily': daily,
        })


# ──── 크롤 상태 ────

class CrawlStatusView(APIView):
    def get(self, request):
        logs = SmartStoreCrawlLog.objects.select_related('account').order_by('-started_at')[:30]
        data = []
        for log in logs:
            data.append({
                'id': log.id,
                'account': log.account.display_name if log.account else '-',
                'status': log.status,
                'message': log.message,
                'started_at': log.started_at.isoformat(),
                'ended_at': log.ended_at.isoformat() if log.ended_at else None,
            })
        return Response(data)
