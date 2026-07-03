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

    # 쿠팡 오픈API (Wing > 오픈API 관리에서 발급, 브라우저 자동화 없이 데이터 조회)
    vendor_id = models.CharField(max_length=20, blank=True, default='', help_text='업체코드 (예: A01122552)')
    access_key = models.CharField(max_length=100, blank=True, default='')
    secret_key = models.CharField(max_length=100, blank=True, default='')
    api_key_expires_at = models.DateTimeField(null=True, blank=True, help_text='오픈API 키 유효기간')

    class Meta:
        db_table = 'coupang_account'
        ordering = ['display_order', 'id']

    def __str__(self):
        return f'{self.seller_name or self.login_id}'

    @property
    def has_api_key(self):
        return bool(self.vendor_id and self.access_key and self.secret_key)


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


class CoupangOrder(models.Model):
    """쿠팡 오픈API 주문(ordersheets) 수집 결과 — 상품/매출 단위."""
    account = models.ForeignKey(CoupangAccount, on_delete=models.CASCADE, related_name='orders')
    order_id = models.CharField(max_length=50)
    shipment_box_id = models.CharField(max_length=50, blank=True, default='')
    ordered_at = models.DateTimeField()
    product_name = models.CharField(max_length=500, blank=True, default='')
    vendor_item_id = models.CharField(max_length=50, blank=True, default='')
    seller_product_id = models.CharField(max_length=50, blank=True, default='')
    quantity = models.IntegerField(default=1)
    sales_price = models.BigIntegerField(default=0, help_text='주문 시 상품가격(1개 기준 orderPrice)')
    status = models.CharField(max_length=30, blank=True, default='')
    collected_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'coupang_order'
        unique_together = [('account', 'order_id', 'vendor_item_id')]
        ordering = ['-ordered_at']
        indexes = [
            models.Index(fields=['account', 'ordered_at']),
        ]

    def __str__(self):
        return f'{self.account.login_id} {self.order_id} {self.product_name[:20]}'


class CoupangProduct(models.Model):
    """쿠팡 오픈API 등록상품 목록 (seller-products)."""
    account = models.ForeignKey(CoupangAccount, on_delete=models.CASCADE, related_name='products')
    seller_product_id = models.CharField(max_length=50)
    product_name = models.CharField(max_length=500, blank=True, default='')
    product_id = models.CharField(max_length=50, blank=True, default='')
    category_id = models.CharField(max_length=50, blank=True, default='')
    brand = models.CharField(max_length=200, blank=True, default='')
    status_name = models.CharField(max_length=30, blank=True, default='', help_text='승인완료/승인반려 등')
    sale_started_at = models.DateTimeField(null=True, blank=True)
    sale_ended_at = models.DateTimeField(null=True, blank=True)
    registered_at = models.DateTimeField(null=True, blank=True)
    collected_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'coupang_product'
        unique_together = [('account', 'seller_product_id')]
        ordering = ['-registered_at']

    def __str__(self):
        return f'{self.account.login_id} {self.product_name[:30]}'
