from django.db import models


class SalesRecord(models.Model):
    # 매칭 안 된 행도 보관하기 위해 seller는 nullable (나중에 하나씩 매칭)
    seller = models.ForeignKey('accounts.SellerAccount', on_delete=models.SET_NULL,
                               null=True, blank=True, related_name='sales_records')
    shop_name = models.CharField(max_length=200, blank=True, default='')   # 파일 원본 쇼핑몰명 (보류/매칭용)
    platform = models.CharField(max_length=20, blank=True, default='')      # 11st/gmarket/auction... (정렬용)
    order_date = models.DateField()
    order_datetime = models.DateTimeField(null=True, blank=True)  # 주문/결제 일시(시간포함) — 중복판별용
    order_number = models.CharField(max_length=100, blank=True)
    product_name = models.CharField(max_length=500)
    product_code = models.CharField(max_length=100, blank=True)
    quantity = models.IntegerField(default=1)
    unit_price = models.IntegerField(default=0)      # 판매가 (참고용)
    total_price = models.IntegerField(default=0)     # 매출 = 정산받는금액
    cost = models.IntegerField(default=0)            # 구매가(원가) = 판매사 주문관리 메모
    commission = models.IntegerField(default=0)      # 마켓수수료
    shipping_fee = models.IntegerField(default=0)
    net_profit = models.IntegerField(default=0)      # 순익 = 매출 - 구매가
    status = models.CharField(max_length=50, default='completed',
                              choices=[('pending', '대기'), ('completed', '완료'), ('cancelled', '취소'), ('returned', '반품')])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sales_records'
        ordering = ['-order_date']
        indexes = [
            models.Index(fields=['-order_date']),
            models.Index(fields=['platform', 'order_date']),
            models.Index(fields=['status', 'order_date']),
            models.Index(fields=['platform', 'status', 'order_date']),
            models.Index(fields=['product_code']),
        ]


class SalesUploadLog(models.Model):
    file_name = models.CharField(max_length=500)
    row_count = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sales_upload_logs'
