import csv
import io
from rest_framework import viewsets, views, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from django.db.models import Sum, Count
from .models import SalesRecord, SalesUploadLog
from .serializers import SalesRecordSerializer, SalesUploadLogSerializer
from apps.accounts.models import SellerAccount


class SalesRecordViewSet(viewsets.ModelViewSet):
    queryset = SalesRecord.objects.select_related('seller').all()
    serializer_class = SalesRecordSerializer
    filterset_fields = ['seller', 'status', 'order_date']
    search_fields = ['product_name', 'product_code', 'order_number']
    ordering_fields = ['order_date', 'total_price']


class SalesUploadView(views.APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES.get('file')
        seller_id = request.data.get('seller')
        if not file or not seller_id:
            return Response({'error': '파일과 셀러를 선택해주세요.'}, status=400)

        try:
            seller = SellerAccount.objects.get(id=seller_id)
        except SellerAccount.DoesNotExist:
            return Response({'error': '셀러를 찾을 수 없습니다.'}, status=404)

        decoded = file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded))

        success, errors_list = 0, []
        for i, row in enumerate(reader, 1):
            try:
                SalesRecord.objects.create(
                    seller=seller,
                    order_date=row.get('주문일', row.get('order_date', '')),
                    order_number=row.get('주문번호', row.get('order_number', '')),
                    product_name=row.get('상품명', row.get('product_name', '')),
                    product_code=row.get('상품코드', row.get('product_code', '')),
                    quantity=int(row.get('수량', row.get('quantity', 1))),
                    unit_price=int(row.get('단가', row.get('unit_price', 0))),
                    total_price=int(row.get('합계', row.get('total_price', 0))),
                    commission=int(row.get('수수료', row.get('commission', 0))),
                    shipping_fee=int(row.get('배송비', row.get('shipping_fee', 0))),
                    net_profit=int(row.get('순이익', row.get('net_profit', 0))),
                )
                success += 1
            except Exception as e:
                errors_list.append(f'행 {i}: {str(e)}')

        log = SalesUploadLog.objects.create(
            file_name=file.name,
            row_count=success + len(errors_list),
            success_count=success,
            error_count=len(errors_list),
            errors=errors_list,
        )
        return Response(SalesUploadLogSerializer(log).data, status=201)


class SalesSummaryView(views.APIView):
    def get(self, request):
        date_from = request.query_params.get('from')
        date_to = request.query_params.get('to')
        qs = SalesRecord.objects.filter(status='completed')
        if date_from:
            qs = qs.filter(order_date__gte=date_from)
        if date_to:
            qs = qs.filter(order_date__lte=date_to)
        summary = qs.aggregate(
            total_revenue=Sum('total_price'),
            total_profit=Sum('net_profit'),
            total_orders=Count('id'),
            total_quantity=Sum('quantity'),
        )
        return Response(summary)


class SalesUploadLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SalesUploadLog.objects.all().order_by('-uploaded_at')
    serializer_class = SalesUploadLogSerializer
