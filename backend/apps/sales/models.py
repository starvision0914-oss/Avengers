from django.db import models


class SalesRecord(models.Model):
    seller = models.ForeignKey('accounts.SellerAccount', on_delete=models.CASCADE, related_name='sales_records')
    order_date = models.DateField()
    order_number = models.CharField(max_length=100, blank=True)
    product_name = models.CharField(max_length=500)
    product_code = models.CharField(max_length=100, blank=True)
    quantity = models.IntegerField(default=1)
    unit_price = models.IntegerField(default=0)
    total_price = models.IntegerField(default=0)
    commission = models.IntegerField(default=0)
    shipping_fee = models.IntegerField(default=0)
    net_profit = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default='completed',
                              choices=[('pending', '대기'), ('completed', '완료'), ('cancelled', '취소'), ('returned', '반품')])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sales_records'
        ordering = ['-order_date']


class SalesUploadLog(models.Model):
    file_name = models.CharField(max_length=500)
    row_count = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sales_upload_logs'
