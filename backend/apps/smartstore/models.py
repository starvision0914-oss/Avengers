from django.db import models


class SmartStoreAccount(models.Model):
    login_id = models.CharField(max_length=200)
    login_pw = models.CharField(max_length=200, blank=True, default='')
    store_name = models.CharField(max_length=200)
    store_slug = models.CharField(max_length=200, blank=True, default='', help_text='스토어 URL ID (네이버ID)')
    display_name = models.CharField(max_length=200, blank=True, default='')
    memo = models.CharField(max_length=300, blank=True, default='')
    commerce_api_key = models.CharField(max_length=200, blank=True, default='', help_text='네이버 커머스 API Client ID')
    commerce_secret_key = models.TextField(blank=True, default='', help_text='네이버 커머스 API Client Secret (bcrypt)')
    merchant_no = models.CharField(max_length=50, blank=True, default='', help_text='스마트스토어 merchantNo (GraphQL)')
    naver_ad_customer_id = models.CharField(max_length=50, blank=True, default='', help_text='네이버 검색광고 CPC Customer ID')
    naver_ad_access_license = models.CharField(max_length=200, blank=True, default='', help_text='네이버 검색광고 CPC Access License')
    naver_ad_secret_key = models.TextField(blank=True, default='', help_text='네이버 검색광고 CPC Secret Key')
    naver_ad_ai_customer_id = models.CharField(max_length=50, blank=True, default='', help_text='네이버 검색광고 AI Customer ID')
    naver_ad_ai_access_license = models.CharField(max_length=200, blank=True, default='', help_text='네이버 검색광고 AI Access License')
    naver_ad_ai_secret_key = models.TextField(blank=True, default='', help_text='네이버 검색광고 AI Secret Key')
    naver_ad_account_id = models.CharField(max_length=50, blank=True, default='', help_text='광고센터 ad-account ID (billing 스크랩용, URL의 /ad-account/숫자 부분)')
    naver_ad_login_id = models.CharField(max_length=100, blank=True, default='', help_text='광고센터 로그인 Naver ID (naver_ads_cookies.json 키와 일치)')
    purchase_rate = models.IntegerField(default=0, help_text='구매가율(%) — 예: 70 입력 시 구매가=매출×70%')
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'smartstore_account'
        ordering = ['display_order', 'id']
        unique_together = [('login_id', 'store_slug')]

    def __str__(self):
        return f"{self.display_name or self.store_name} ({self.login_id})"


class SmartStoreSales(models.Model):
    """일별 판매 통계 (정산 기준)"""
    account = models.ForeignKey(SmartStoreAccount, on_delete=models.CASCADE, related_name='sales')
    date = models.DateField()
    order_count = models.IntegerField(default=0)
    sales_amount = models.BigIntegerField(default=0, help_text='결제금액')
    cancel_amount = models.BigIntegerField(default=0, help_text='취소금액')
    return_amount = models.BigIntegerField(default=0, help_text='반품금액')
    settlement_amount = models.BigIntegerField(default=0, help_text='정산예정금액')
    commission_amount = models.BigIntegerField(default=0, help_text='수수료')
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'smartstore_sales'
        unique_together = [('account', 'date')]
        indexes = [models.Index(fields=['account', 'date'])]


class SmartStoreAdCost(models.Model):
    """일별 광고비 — ad_type: cpc(검색/클릭형) | ai(AI추천/스마트쇼핑) | brand(브랜드검색)"""
    AD_TYPE_CHOICES = [
        ('cpc', 'CPC(검색/클릭형)'),
        ('ai', 'AI(스마트쇼핑/AI추천)'),
        ('brand', '브랜드검색'),
    ]
    account = models.ForeignKey(SmartStoreAccount, on_delete=models.CASCADE, related_name='ad_costs')
    date = models.DateField()
    ad_type = models.CharField(max_length=20, choices=AD_TYPE_CHOICES, default='cpc')
    cost = models.BigIntegerField(default=0)
    impression = models.IntegerField(default=0)
    click = models.IntegerField(default=0)
    conversion_count = models.IntegerField(default=0)
    conversion_amount = models.BigIntegerField(default=0)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'smartstore_ad_cost'
        unique_together = [('account', 'date', 'ad_type')]
        indexes = [models.Index(fields=['account', 'date'])]


class SmartStoreProduct(models.Model):
    """스마트스토어 상품 목록 (내부 API 수집)"""
    STATUS_CHOICES = [
        ('SALE', '판매중'),
        ('SUSPENSION', '판매중지'),
        ('OUTOFSTOCK', '품절'),
        ('WAIT', '승인대기'),
        ('PROHIBITION', '판매금지'),
    ]
    account = models.ForeignKey(SmartStoreAccount, on_delete=models.CASCADE, related_name='products')
    product_no = models.CharField(max_length=100, help_text='originProductNo')
    channel_product_no = models.CharField(max_length=100, blank=True, default='')
    name = models.CharField(max_length=500)
    sale_price = models.IntegerField(default=0)
    stock_quantity = models.IntegerField(default=0)
    status_type = models.CharField(max_length=50, default='')
    seller_management_code = models.CharField(max_length=200, blank=True, default='')
    category_id = models.CharField(max_length=100, blank=True, default='')
    product_image_url = models.TextField(blank=True, default='')
    ownerclan_soldout = models.BooleanField(default=False, help_text='오너클랜 품절 여부 (W코드 자동처리 대상)')
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'smartstore_product'
        unique_together = [('account', 'product_no')]
        indexes = [
            models.Index(fields=['account', 'status_type']),
            models.Index(fields=['seller_management_code']),
        ]

    def __str__(self):
        return f"{self.name} ({self.product_no})"


class SmartStoreCrawlLog(models.Model):
    STATUS_CHOICES = [('running', '실행중'), ('done', '완료'), ('error', '오류')]
    account = models.ForeignKey(SmartStoreAccount, on_delete=models.CASCADE, related_name='crawl_logs', null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    message = models.TextField(blank=True, default='')
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'smartstore_crawl_log'
        ordering = ['-started_at']
