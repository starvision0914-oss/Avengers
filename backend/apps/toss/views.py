import datetime

from django.db.models import Sum, Count
from rest_framework import views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.toss.models import TossAccount, TossAdCost, TossCampaignAdCost


def _default_range():
    today = datetime.date.today()
    end = today - datetime.timedelta(days=1)
    start = end.replace(day=1)
    return start, end


def _parse_range(request):
    start = request.query_params.get('start')
    end = request.query_params.get('end')
    if not start or not end:
        return _default_range()
    return datetime.date.fromisoformat(start), datetime.date.fromisoformat(end)


class TossAccountsView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        accounts = TossAccount.objects.filter(is_active=True).order_by('display_order', 'id')
        return Response([{
            'id': a.id, 'login_id': a.login_id, 'seller_name': a.seller_name or a.login_id,
            'last_crawled_at': a.last_crawled_at,
        } for a in accounts])


class TossDashboardView(views.APIView):
    """일자별/월별 광고비 요약. group=day(기본)|month"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start, end = _parse_range(request)
        group = request.query_params.get('group', 'day')

        qs = TossAdCost.objects.filter(date__gte=start, date__lte=end)
        totals = qs.aggregate(
            exec_ad_cost=Sum('exec_ad_cost'), conversion_amount=Sum('conversion_amount'),
            impressions=Sum('impressions'), clicks=Sum('clicks'),
        )
        for k in totals:
            totals[k] = totals[k] or 0
        if start == end:
            single = qs.first()
            totals['roas'] = float(single.effective_roas) if single else None
        else:
            totals['roas'] = round(totals['conversion_amount'] / totals['exec_ad_cost'] * 100, 1) if totals['exec_ad_cost'] else None

        rows = []
        if group == 'month':
            agg = {}
            for r in qs.values('date').annotate(
                exec_ad_cost=Sum('exec_ad_cost'), conversion_amount=Sum('conversion_amount'),
                impressions=Sum('impressions'), clicks=Sum('clicks'),
            ):
                key = r['date'].strftime('%Y-%m')
                a = agg.setdefault(key, {'period': key, 'exec_ad_cost': 0, 'conversion_amount': 0, 'impressions': 0, 'clicks': 0})
                a['exec_ad_cost'] += r['exec_ad_cost'] or 0
                a['conversion_amount'] += r['conversion_amount'] or 0
                a['impressions'] += r['impressions'] or 0
                a['clicks'] += r['clicks'] or 0
            rows = sorted(agg.values(), key=lambda x: x['period'], reverse=True)
        else:
            # 날짜당 계정 1개뿐이면 유효광고수익률은 실제 사이트 카드값(effective_roas)을 그대로 쓰고,
            # 계정이 여러 개로 늘면 그 합만 비율로 근사(정확한 가중공식은 토스 비공개).
            single_roas = {a.date: a.effective_roas for a in qs} if qs.values('account').distinct().count() <= 1 else {}
            for r in qs.values('date').annotate(
                exec_ad_cost=Sum('exec_ad_cost'), conversion_amount=Sum('conversion_amount'),
                impressions=Sum('impressions'), clicks=Sum('clicks'),
            ).order_by('-date'):
                rows.append({
                    'period': r['date'].isoformat(),
                    'exec_ad_cost': r['exec_ad_cost'] or 0,
                    'conversion_amount': r['conversion_amount'] or 0,
                    'impressions': r['impressions'] or 0,
                    'clicks': r['clicks'] or 0,
                    '_roas_override': float(single_roas[r['date']]) if r['date'] in single_roas else None,
                })
        for r in rows:
            override = r.pop('_roas_override', None)
            r['roas'] = override if override is not None else (
                round(r['conversion_amount'] / r['exec_ad_cost'] * 100, 1) if r['exec_ad_cost'] else None)

        return Response({'start': start.isoformat(), 'end': end.isoformat(), 'group': group, 'totals': totals, 'rows': rows})


class TossCampaignListView(views.APIView):
    """선택 기간 내 캠페인별 합계 — '전체 내역'."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start, end = _parse_range(request)
        qs = TossCampaignAdCost.objects.filter(date__gte=start, date__lte=end)
        agg = {}
        for r in qs.order_by('date'):
            key = r.campaign_id or r.campaign_name
            a = agg.setdefault(key, {
                'campaign_id': r.campaign_id, 'campaign_name': r.campaign_name, 'status': r.status,
                'exec_ad_cost': 0, 'conversion_amount': 0, 'impressions': 0, 'clicks': 0,
                'conv_qty': 0, 'conv_orders': 0, 'start_date': r.start_date, 'end_date': r.end_date,
            })
            a['status'] = r.status
            a['exec_ad_cost'] += r.exec_ad_cost
            a['conversion_amount'] += r.conversion_amount
            a['impressions'] += r.impressions
            a['clicks'] += r.clicks
            a['conv_qty'] += r.conv_qty
            a['conv_orders'] += r.conv_orders
        rows = list(agg.values())
        for r in rows:
            r['roas'] = round(r['conversion_amount'] / r['exec_ad_cost'] * 100, 1) if r['exec_ad_cost'] else None
        rows.sort(key=lambda x: x['exec_ad_cost'], reverse=True)
        return Response({'start': start.isoformat(), 'end': end.isoformat(), 'rows': rows})


class TossAccountSummaryView(views.APIView):
    """계정별 요약 — 스마트스토어 대시보드(by_account)와 동일 구조.
    매출/구매는 SalesRecord(platform='25.토스몰'), 광고비는 TossAdCost 기준.
    등록상품수: 토스는 아직 상품목록 수집기가 없어 None(-)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.accounts.models import SellerAccount
        from apps.sales.models import SalesRecord

        start, end = _parse_range(request)

        toss_accounts = list(TossAccount.objects.filter(is_active=True).order_by('display_order', 'id'))
        seller_accounts = SellerAccount.objects.filter(platform='25.토스몰')
        seller_id_to_login = {a.id: a.seller_id for a in seller_accounts}

        by_login = {a.login_id: {
            'sales': 0, 'settlement': 0, 'orders': 0, 'commission': 0,
            'ad_cost': 0, 'conversion_amount': 0,
        } for a in toss_accounts}

        sr_qs = SalesRecord.objects.filter(platform='25.토스몰', order_date__gte=start, order_date__lte=end)
        for r in sr_qs.values('seller_id').annotate(
            sales=Sum('total_price'), commission=Sum('commission'), orders=Count('id'),
        ):
            login = seller_id_to_login.get(r['seller_id'])
            if not login or login not in by_login:
                continue
            sales = r['sales'] or 0
            commission = r['commission'] or 0
            by_login[login]['sales'] += sales
            by_login[login]['settlement'] += sales - commission
            by_login[login]['commission'] += commission
            by_login[login]['orders'] += r['orders'] or 0

        ad_qs = TossAdCost.objects.filter(date__gte=start, date__lte=end)
        for row in ad_qs.values('account__login_id').annotate(
            cost=Sum('exec_ad_cost'), conv=Sum('conversion_amount'),
        ):
            login = row['account__login_id']
            if login not in by_login:
                continue
            by_login[login]['ad_cost'] += row['cost'] or 0
            by_login[login]['conversion_amount'] += row['conv'] or 0

        now = datetime.datetime.now()
        account_list = []
        for a in toss_accounts:
            row = by_login[a.login_id]
            ad = row['ad_cost']
            if a.last_crawled_at is None:
                note = '수집 전'
            elif (now - a.last_crawled_at.replace(tzinfo=None)).days >= 2:
                note = '수집 확인 필요'
            else:
                note = '정상'
            account_list.append({
                'account_id': a.id,
                'login_id': a.login_id,
                'account_name': a.seller_name or a.login_id,
                'sales': row['sales'],
                'settlement': row['settlement'],
                'orders': row['orders'],
                'ad_cost': ad,
                'roas': round(row['sales'] / ad * 100, 1) if ad > 0 else None,
                'registered_products': None,
                'note': note,
            })

        return Response({
            'period': {'start': start.isoformat(), 'end': end.isoformat()},
            'by_account': account_list,
        })
