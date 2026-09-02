from django.db import models


class TossAccount(models.Model):
    """토스 셀러(shopping-seller.toss.im) 계정 — 광고센터 별도 로그인 없이 토스 계정 그대로 사용."""
    login_id = models.CharField(max_length=150, unique=True, help_text='이메일 또는 전화번호')
    login_pw = models.CharField(max_length=200, blank=True, default='')
    seller_name = models.CharField(max_length=100, blank=True, default='')
    is_active = models.BooleanField(default=True)
    cookie_data = models.TextField(blank=True, default='')
    cookie_saved_at = models.DateTimeField(null=True, blank=True)
    last_crawled_at = models.DateTimeField(null=True, blank=True)
    fail_count = models.IntegerField(default=0)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'toss_account'
        ordering = ['display_order', 'id']

    def __str__(self):
        return self.seller_name or self.login_id


class TossAdCost(models.Model):
    """토스쇼핑 파트너스 > 상품 광고(/ads) 일별 집행 광고비 총계."""
    account = models.ForeignKey(TossAccount, on_delete=models.CASCADE, related_name='ad_costs')
    date = models.DateField(db_index=True)
    exec_ad_cost = models.BigIntegerField(default=0, help_text='집행 광고비')
    conversion_amount = models.BigIntegerField(default=0, help_text='광고 전환 거래액')
    effective_roas = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='유효 광고 수익률(%)')
    impressions = models.IntegerField(default=0, help_text='노출 수')
    clicks = models.IntegerField(default=0, help_text='클릭 수')
    collected_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'toss_ad_cost'
        unique_together = [('account', 'date')]
        ordering = ['-date']
        indexes = [models.Index(fields=['account', 'date'])]

    def __str__(self):
        return f'{self.account.login_id} {self.date}'


class TossCampaignAdCost(models.Model):
    """토스 캠페인별 광고비(전체 캠페인 목록, 일 단위 스냅샷) — '전체 내역'."""
    account = models.ForeignKey(TossAccount, on_delete=models.CASCADE, related_name='campaign_ad_costs')
    date = models.DateField(db_index=True)
    campaign_id = models.CharField(max_length=50, blank=True, default='')
    campaign_name = models.CharField(max_length=200, blank=True, default='')
    status = models.CharField(max_length=30, blank=True, default='')
    exec_ad_cost = models.BigIntegerField(default=0)
    conversion_amount = models.BigIntegerField(default=0)
    effective_roas = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    ctr = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    conv_qty = models.IntegerField(default=0)
    conv_orders = models.IntegerField(default=0)
    conv_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    cpc = models.IntegerField(default=0)
    start_date = models.CharField(max_length=20, blank=True, default='')
    end_date = models.CharField(max_length=20, blank=True, default='')
    collected_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'toss_campaign_ad_cost'
        unique_together = [('account', 'date', 'campaign_id')]
        ordering = ['-date']
        indexes = [models.Index(fields=['account', 'date'])]

    def __str__(self):
        return f'{self.account.login_id} {self.date} {self.campaign_name}'
