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


class GmarketAiAdSummary(models.Model):
    """지마켓 AI 광고 상태 요약"""
    gmarket_id = models.CharField(max_length=50)
    seller_id = models.CharField(max_length=50)
    group_name = models.CharField(max_length=200, blank=True)
    button_status = models.CharField(max_length=10, default='OFF')
    actual_status = models.CharField(max_length=10, default='OFF')
    actual_reason = models.CharField(max_length=100, blank=True)
    start_date = models.CharField(max_length=20, blank=True)
    end_date = models.CharField(max_length=20, blank=True)
    operation_status = models.CharField(max_length=200, blank=True)
    budget_mgmt = models.CharField(max_length=200, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'gmarket_ai_ad_summary'
        ordering = ['-updated_at']

class GmarketAiAdHistory(models.Model):
    """지마켓 AI 광고 ON/OFF 이력"""
    gmarket_id = models.CharField(max_length=50)
    seller_id = models.CharField(max_length=50)
    group_name = models.CharField(max_length=200, blank=True)
    event_time = models.DateTimeField()
    history_type = models.CharField(max_length=100, blank=True)
    detail = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'gmarket_ai_ad_history'
        ordering = ['-event_time']

class St11AdofficeCampaign(models.Model):
    """11번가 Adoffice 캠페인 데이터"""
    eleven_id = models.CharField(max_length=50)
    campaign_name = models.CharField(max_length=200)
    is_ai = models.BooleanField(default=False)
    onoff = models.BooleanField(default=False)
    status = models.CharField(max_length=50, blank=True)
    daily_budget = models.IntegerField(null=True, blank=True)
    target_roas = models.IntegerField(null=True, blank=True)
    exposure_period = models.CharField(max_length=100, blank=True)
    impressions = models.IntegerField(null=True, blank=True)
    clicks = models.IntegerField(null=True, blank=True)
    ctr = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    avg_rank = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    avg_cpc = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_cost = models.IntegerField(null=True, blank=True)
    total_conversions = models.IntegerField(null=True, blank=True)
    cost_per_conversion = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_conv_amount = models.IntegerField(null=True, blank=True)
    total_conv_rate = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    total_roas_pct = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    direct_conversions = models.IntegerField(null=True, blank=True)
    direct_conv_rate = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    direct_conv_amount = models.IntegerField(null=True, blank=True)
    direct_cost_per_conv = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    direct_roas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    indirect_conversions = models.IntegerField(null=True, blank=True)
    indirect_cost_per_conv = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    indirect_conv_amount = models.IntegerField(null=True, blank=True)
    indirect_conv_rate = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    indirect_roas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    campaign_registered_at = models.CharField(max_length=50, blank=True)
    collected_at = models.DateTimeField()
    class Meta:
        db_table = 'st11_adoffice_campaign'
        ordering = ['-collected_at']
        indexes = [
            models.Index(fields=['eleven_id']),
            models.Index(fields=['collected_at']),
        ]

class St11AiAdHistory(models.Model):
    """11번가 AI 광고 ON/OFF 이력"""
    seller_id = models.CharField(max_length=50)
    action = models.CharField(max_length=20, blank=True)
    campaign_name = models.CharField(max_length=200, blank=True)
    before_status = models.CharField(max_length=10, blank=True)
    after_status = models.CharField(max_length=10, blank=True)
    source = models.CharField(max_length=50, blank=True)
    event_time = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'st11_ai_ad_history'
        ordering = ['-event_time']


class GmarketCpcAdStatus(models.Model):
    """간편광고/일반광고 ON/OFF 현황"""
    gmarket_id = models.CharField(max_length=50, unique=True)
    cpc1_on = models.IntegerField(default=0)
    cpc1_off = models.IntegerField(default=0)
    cpc2_on = models.IntegerField(default=0)
    cpc2_off = models.IntegerField(default=0)
    collected_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'gmarket_cpc_ad_status'

class Cpc2Schedule(models.Model):
    """간편광고 ON/OFF 예약 설정 (싱글톤)"""
    on_time = models.TimeField(null=True, blank=True)
    off_time = models.TimeField(null=True, blank=True)
    skip_holidays = models.BooleanField(default=True)
    selected_accounts = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'gmarket_cpc2_schedule'

class Cpc2History(models.Model):
    """간편광고 ON/OFF 이력"""
    gmarket_id = models.CharField(max_length=50)
    action = models.CharField(max_length=5)
    cpc2_before = models.IntegerField(default=0)
    cpc2_after = models.IntegerField(default=0)
    source = models.CharField(max_length=20, default='manual')
    event_time = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'gmarket_cpc2_history'
        ordering = ['-event_time']

class CppSchedule(models.Model):
    """프라임 입찰기간 변경 예약 (싱글톤)"""
    enabled = models.BooleanField(default=False)
    weekday_num = models.IntegerField(default=3)
    run_time = models.TimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'gmarket_cpp_schedule'

class CppBidHistory(models.Model):
    """프라임 입찰기간 변경 이력"""
    gmarket_id = models.CharField(max_length=50)
    keyword_count = models.IntegerField(default=0)
    bid_start_date = models.DateField(null=True, blank=True)
    bid_end_date = models.DateField(null=True, blank=True)
    source = models.CharField(max_length=20, default='manual')
    success = models.BooleanField(default=False)
    detail = models.TextField(blank=True)
    event_time = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'gmarket_cpp_bid_history'
        ordering = ['-event_time']

class AiSchedule(models.Model):
    """AI 광고 ON/OFF 예약 설정"""
    platform = models.CharField(max_length=20, choices=[('gmarket','Gmarket'),('11st','11번가')])
    on_time = models.TimeField(null=True, blank=True)
    off_time = models.TimeField(null=True, blank=True)
    skip_holidays = models.BooleanField(default=True)
    selected_accounts = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'ai_schedule'
        unique_together = [('platform',)]

class TelegramConfig(models.Model):
    """텔레그램 알림 설정 (싱글톤)"""
    bot_token = models.CharField(max_length=200, blank=True)
    mode = models.CharField(max_length=10, default='off', choices=[('off','OFF'),('change','변동감지'),('15m','15분'),('1h','1시간')])
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'telegram_config'

class TelegramRecipient(models.Model):
    """텔레그램 수신자"""
    chat_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    auto_send = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'telegram_recipients'

class SellerGroup(models.Model):
    """집중관리 셀러 그룹"""
    name = models.CharField(max_length=100, default='집중')
    seller_ids = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'seller_groups'

class CronSchedule(models.Model):
    """자동 수집 스케줄 설정"""
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    command = models.CharField(max_length=200)
    cron_expr = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=False)
    description = models.CharField(max_length=255, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'cron_schedules'
        ordering = ['name']

class ReceivedSmsMessage(models.Model):
    """SMS 수신 메시지 (OTP 인증용)"""
    csphone_number = models.CharField(max_length=20, blank=True)
    checkphone_number = models.CharField(max_length=20, blank=True)
    message = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    setting_id = models.IntegerField(default=1)
    class Meta:
        db_table = 'received_sms_message'
        ordering = ['-received_at']


class SmsPhoneSetting(models.Model):
    """SMS 수신 전화번호 설정"""
    phone_number = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'sms_phone_settings'
        ordering = ['phone_number']
