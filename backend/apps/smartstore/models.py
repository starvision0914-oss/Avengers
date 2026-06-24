from django.db import models


class SmartStoreAccount(models.Model):
    login_id = models.CharField(max_length=200)
    login_pw = models.CharField(max_length=200, blank=True, default='')
    store_name = models.CharField(max_length=200)
    store_slug = models.CharField(max_length=200, blank=True, default='', help_text='스토어 URL ID (네이버ID)')
    display_name = models.CharField(max_length=200, blank=True, default='')
    memo = models.CharField(max_length=300, blank=True, default='')
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
    """일별 광고비 (쇼핑검색/클릭형)"""
    AD_TYPE_CHOICES = [
        ('shopping', '쇼핑검색'),
        ('click', '클릭형'),
        ('brand', '브랜드검색'),
    ]
    account = models.ForeignKey(SmartStoreAccount, on_delete=models.CASCADE, related_name='ad_costs')
    date = models.DateField()
    ad_type = models.CharField(max_length=20, choices=AD_TYPE_CHOICES, default='shopping')
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
