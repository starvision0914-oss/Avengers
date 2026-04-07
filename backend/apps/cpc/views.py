from rest_framework import viewsets, views, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from .models import CPCDailyCost, CPCDeposit, CPCTransaction
from .serializers import CPCDailyCostSerializer, CPCDepositSerializer, CPCTransactionSerializer


class CPCDailyCostViewSet(viewsets.ModelViewSet):
    queryset = CPCDailyCost.objects.select_related('seller').all()
    serializer_class = CPCDailyCostSerializer
    filterset_fields = ['seller', 'date']
    search_fields = ['seller__seller_id', 'seller__seller_name']
    ordering_fields = ['date', 'total_cost']


class CPCDepositViewSet(viewsets.ModelViewSet):
    queryset = CPCDeposit.objects.select_related('seller').all()
    serializer_class = CPCDepositSerializer
    filterset_fields = ['seller', 'deposit_date']


class CPCTransactionViewSet(viewsets.ModelViewSet):
    queryset = CPCTransaction.objects.select_related('seller').all()
    serializer_class = CPCTransactionSerializer
    filterset_fields = ['seller', 'category']
    ordering_fields = ['transaction_time', 'amount']


class CPCSummaryView(views.APIView):
    def get(self, request):
        date = request.query_params.get('date')
        qs = CPCDailyCost.objects.select_related('seller')
        if date:
            qs = qs.filter(date=date)
        summary = qs.values('seller__seller_id', 'seller__seller_name').annotate(
            total_cpc=Sum('cpc_cost'),
            total_ai=Sum('ai_cost'),
            total_cost=Sum('total_cost'),
            total_clicks=Sum('clicks'),
        ).order_by('seller__seller_id')

        deposits = {}
        for d in CPCDeposit.objects.values('seller__seller_id').annotate(latest_balance=Sum('balance')):
            deposits[d['seller__seller_id']] = d['latest_balance']

        result = []
        for s in summary:
            sid = s['seller__seller_id']
            s['balance'] = deposits.get(sid, 0)
            result.append(s)
        return Response(result)


class CPCChartView(views.APIView):
    def get(self, request):
        date = request.query_params.get('date')
        seller_id = request.query_params.get('seller')
        qs = CPCDailyCost.objects.all()
        if date:
            qs = qs.filter(date=date)
        if seller_id:
            qs = qs.filter(seller_id=seller_id)
        data = qs.values('date').annotate(
            total_cpc=Sum('cpc_cost'),
            total_ai=Sum('ai_cost'),
            total_cost=Sum('total_cost'),
        ).order_by('date')
        return Response(list(data))
