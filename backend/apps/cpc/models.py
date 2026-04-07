from django.db import models


class CPCDailyCost(models.Model):
    seller = models.ForeignKey('accounts.SellerAccount', on_delete=models.CASCADE, related_name='cpc_daily_costs')
    date = models.DateField()
    cpc_cost = models.IntegerField(default=0)
    ai_cost = models.IntegerField(default=0)
    total_cost = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    impressions = models.IntegerField(default=0)
    conversions = models.IntegerField(default=0)
    roas = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cpc_daily_costs'
        unique_together = ['seller', 'date']
        ordering = ['-date']


class CPCDeposit(models.Model):
    seller = models.ForeignKey('accounts.SellerAccount', on_delete=models.CASCADE, related_name='cpc_deposits')
    balance = models.IntegerField(default=0)
    deposited_amount = models.IntegerField(default=0)
    deposit_date = models.DateField()
    memo = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cpc_deposits'
        ordering = ['-deposit_date']


class CPCTransaction(models.Model):
    seller = models.ForeignKey('accounts.SellerAccount', on_delete=models.CASCADE, related_name='cpc_transactions')
    transaction_time = models.DateTimeField()
    category = models.CharField(max_length=30, choices=[('CPC', 'CPC'), ('AI', 'AI'), ('서버이용료', '서버이용료'), ('기타', '기타')])
    description = models.CharField(max_length=255, blank=True)
    amount = models.IntegerField(default=0)
    product_code = models.CharField(max_length=100, blank=True)
    product_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cpc_transactions'
        ordering = ['-transaction_time']


class CrawlerAccount(models.Model):
    """크롤러 계정 - fail_count 30 이상이면 차단됨"""
    PLATFORM_CHOICES = [('gmarket', 'Gmarket'), ('11st', '11번가')]
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    login_id = models.CharField(max_length=50)
    password_enc = models.TextField(blank=True)
    seller_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    is_multi_id = models.BooleanField(default=False)
    fail_count = models.IntegerField(default=0)
    crawling_status = models.CharField(max_length=20, default='정상')
    last_crawled_at = models.DateTimeField(null=True, blank=True)
    cookie_data = models.TextField(blank=True)
    cookie_saved_at = models.DateTimeField(null=True, blank=True)
    sub_accounts = models.TextField(default='[]', blank=True)
    gmarket_origin_id = models.CharField(max_length=50, null=True, blank=True)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'crawler_accounts'
        unique_together = [('platform', 'login_id')]
        ordering = ['display_order']


class CrawlerLog(models.Model):
    platform = models.CharField(max_length=20)
    level = models.CharField(max_length=10, default='info')
    message = models.TextField()
    account_id = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'crawler_logs'
        ordering = ['-created_at']


class GmarketDepositSnapshot(models.Model):
    gmarket_id = models.CharField(max_length=50)
    total_balance = models.IntegerField(default=0)
    cash_balance = models.IntegerField(default=0)
    card_balance = models.IntegerField(default=0)
    ad_balance = models.IntegerField(default=0)
    event_balance = models.IntegerField(default=0)
    gmarket_cpc = models.IntegerField(default=0)
    auction_cpc = models.IntegerField(default=0)
    ai_usage = models.IntegerField(default=0)
    total_usage = models.IntegerField(default=0)
    collected_at = models.DateTimeField()
    class Meta:
        db_table = 'gmarket_deposit_snapshots'
        ordering = ['-collected_at']


class ElevenCostHistory(models.Model):
    seller_id = models.CharField(max_length=50)
    transaction_datetime = models.DateTimeField()
    transaction_type = models.CharField(max_length=20)
    raw_description = models.CharField(max_length=255, blank=True)
    amount = models.IntegerField(default=0)
    balance = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'eleven_sellerpoint_history'
        unique_together = [('seller_id', 'transaction_datetime')]
        ordering = ['-transaction_datetime']


class GmarketSellerGrade(models.Model):
    gmarket_id = models.CharField(max_length=50)
    seller_id = models.CharField(max_length=50, blank=True)
    seller_grade = models.CharField(max_length=50, blank=True)
    max_item_count = models.IntegerField(null=True, blank=True)
    approval_status = models.CharField(max_length=50, blank=True)
    contact_expiry = models.CharField(max_length=50, blank=True)
    collected_at = models.DateTimeField()
    class Meta:
        db_table = 'gmarket_seller_grades'
        ordering = ['-collected_at']

class ElevenSellerGrade(models.Model):
    eleven_id = models.CharField(max_length=50)
    seller_name = models.CharField(max_length=100, blank=True)
    grade = models.IntegerField(null=True, blank=True)
    grade_img_src = models.CharField(max_length=500, blank=True)
    required_sales = models.IntegerField(null=True, blank=True)
    grade_message = models.CharField(max_length=255, blank=True)
    collected_at = models.DateTimeField()
    class Meta:
        db_table = 'eleven_seller_grades'
        ordering = ['-collected_at']
