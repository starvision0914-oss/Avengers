from django.db import models


class CoupangAccount(models.Model):
    """쿠팡 Wing 셀러 계정"""
    login_id = models.CharField(max_length=100, unique=True)
    login_pw = models.CharField(max_length=200, blank=True, default='')
    seller_name = models.CharField(max_length=100, blank=True, default='')
    is_rocket_growth = models.BooleanField(default=False, help_text='로켓그로스 사용 계정 여부')
    is_active = models.BooleanField(default=True)
    cookie_data = models.TextField(blank=True, default='')
    cookie_saved_at = models.DateTimeField(null=True, blank=True)
    last_crawled_at = models.DateTimeField(null=True, blank=True)
    fail_count = models.IntegerField(default=0)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'coupang_account'
        ordering = ['display_order', 'id']

    def __str__(self):
        return f'{self.seller_name or self.login_id}'


class CoupangVatSales(models.Model):
    """쿠팡 부가세신고 매출자료 (판매자윙 / 로켓그로스)"""
    SALE_TYPE_CHOICES = [('판매자윙', '판매자윙'), ('로켓그로스', '로켓그로스')]

    account = models.ForeignKey(CoupangAccount, on_delete=models.CASCADE, related_name='vat_sales')
    year = models.IntegerField()
    month = models.IntegerField()
    sale_type = models.CharField(max_length=20, choices=SALE_TYPE_CHOICES)
    credit_card = models.BigIntegerField(default=0)
    cash_receipt = models.BigIntegerField(default=0)
    etc_payment = models.BigIntegerField(default=0)
    total_sales = models.BigIntegerField(default=0)
    collected_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'coupang_vat_sales'
        unique_together = [('account', 'year', 'month', 'sale_type')]
        ordering = ['-year', '-month']
        indexes = [
            models.Index(fields=['account', 'year', 'month']),
        ]

    def __str__(self):
        return f'{self.account.login_id} {self.year}-{self.month:02d} {self.sale_type}'
