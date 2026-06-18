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
    cost_type = models.CharField(max_length=20, default='sellerpoint', choices=[('sellerpoint','셀러포인트'),('sellercash','셀러캐시')])
    display_order = models.IntegerField(default=0)
    is_focused = models.BooleanField(default=False, help_text='집중관리 대상 표시')
    api_key = models.CharField(max_length=200, blank=True, default='', help_text='11번가 셀러 OpenAPI 키')
    connect_fail_count = models.IntegerField(default=0, help_text='연속 접속(로그인) 실패 횟수 - 3회 도달 시 실패 표시')
    last_otp_at = models.DateTimeField(null=True, blank=True, help_text='마지막 OTP 인증 완료 시각 (11번가 OTP는 24시간 유지)')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'crawler_accounts'
        unique_together = [('platform', 'login_id')]
        ordering = ['display_order']

    # 접속 실패 한계 (이 횟수만큼 연속 실패하면 해당 계정 중지 후 다음 계정으로)
    CONNECT_FAIL_LIMIT = 3

    def mark_connect_failed(self):
        """접속(로그인) 실패 1회 누적. 한계 도달 시 crawling_status='실패'.
        반환값: 한계 도달로 '실패' 처리되었으면 True."""
        self.connect_fail_count = (self.connect_fail_count or 0) + 1
        reached = self.connect_fail_count >= self.CONNECT_FAIL_LIMIT
        if reached:
            self.crawling_status = '실패'
        self.save(update_fields=['connect_fail_count', 'crawling_status'])
        return reached

    def reset_connect_fail(self):
        """접속 성공 시 카운터 리셋 (status가 '실패'였다면 '정상'으로 복구)."""
        changed = False
        if self.connect_fail_count:
            self.connect_fail_count = 0
            changed = True
        if self.crawling_status == '실패':
            self.crawling_status = '정상'
            changed = True
        if changed:
            self.save(update_fields=['connect_fail_count', 'crawling_status'])


class CrawlerLog(models.Model):
    platform = models.CharField(max_length=20)
    level = models.CharField(max_length=10, default='info')
    message = models.TextField()
    account_id = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'crawler_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['platform', 'level', '-created_at']),
        ]


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
        indexes = [
            models.Index(fields=['gmarket_id', '-collected_at']),
        ]


class ElevenCostHistory(models.Model):
    seller_id = models.CharField(max_length=50)
    transaction_datetime = models.DateTimeField()
    seq = models.IntegerField(default=0, help_text='같은 거래시각 내 순번 (같은 초 다중 거래 구분)')
    transaction_type = models.CharField(max_length=20)
    raw_description = models.CharField(max_length=255, blank=True)
    amount = models.IntegerField(default=0)
    balance = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'eleven_sellerpoint_history'
        unique_together = [('seller_id', 'transaction_datetime', 'seq')]
        ordering = ['-transaction_datetime']
        indexes = [
            models.Index(fields=['transaction_type', 'transaction_datetime']),
        ]


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


class St11AdStrategyLog(models.Model):
    """11번가 광고 그룹 전략설정(노출 스케줄) 실행 로그.
    run_id = 한 번의 '전략 적용 실행' 단위. status: START/INFO/APPLIED/SKIP/ERROR/DONE."""
    run_id = models.CharField(max_length=40, db_index=True)
    eleven_id = models.CharField(max_length=50, blank=True)
    campaign_name = models.CharField(max_length=200, blank=True)
    group_name = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20)
    detail = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'st11_ad_strategy_log'
        ordering = ['id']
        indexes = [models.Index(fields=['run_id']), models.Index(fields=['created_at'])]


class St11AdStrategySchedule(models.Model):
    """11번가 광고그룹 노출 스케줄 전략 저장(예약).
    저장해두면 폼이 기억하고, cron이 enabled일 때 매일(선택 요일) 자동 재적용한다.
    노출 스케줄은 11번가 측에 주간 단위로 박히지만, 계정/캠페인이 늘거나 초기화될 수 있어 주기 재적용으로 안전망."""
    name = models.CharField(max_length=100, default='기본 전략', blank=True)
    accounts = models.JSONField(default=list, blank=True)      # 적용 대상 11번가 login_id 목록
    campaigns = models.JSONField(default=list, blank=True)     # 적용 대상 캠페인명 목록
    on_start = models.IntegerField(default=8)                  # ON 시작 시(0~23)
    on_end = models.IntegerField(default=16)                   # ON 종료 시(0~23)
    weekdays = models.JSONField(default=list, blank=True)      # ON 요일 [1=월..7=일], 빈값=매일
    enabled = models.BooleanField(default=False)               # cron 자동 재적용 ON/OFF
    last_applied_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'st11_ad_strategy_schedule'
        ordering = ['-updated_at']


class St11ProductRoas(models.Model):
    """11번가 adoffice 다운로드보고서 기반 상품코드별 광고 ROAS (캠페인>상품>키워드 집계)."""
    eleven_id = models.CharField(max_length=50)
    product_no = models.CharField(max_length=50)            # 상품번호(상품코드)
    period = models.CharField(max_length=20)                # 예: 2026-05 (월별)
    campaign_name = models.CharField(max_length=255, blank=True)  # 대표 캠페인명
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    cost = models.BigIntegerField(default=0)               # 총비용(광고비)
    conversions = models.IntegerField(default=0)           # 총전환수
    conv_amount = models.BigIntegerField(default=0)        # 총전환금액
    roas_pct = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # 총광고수익률
    keyword_count = models.IntegerField(default=0)         # 합쳐진 키워드 행 수
    collected_at = models.DateTimeField()

    class Meta:
        db_table = 'st11_product_roas'
        ordering = ['-collected_at']
        indexes = [
            models.Index(fields=['eleven_id', 'period']),
            models.Index(fields=['collected_at']),
        ]


class St11ProductDaily(models.Model):
    """11번가 adoffice 일별 상품코드별 광고 지표 — (계정,상품,날짜) 단위 누적.
    중복 없음(unique). ROAS는 비가산이라 저장 안 함(조회 시 합산 후 계산)."""
    eleven_id = models.CharField(max_length=50)
    product_no = models.CharField(max_length=50)
    stat_date = models.DateField()
    campaign_name = models.CharField(max_length=255, blank=True)
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    cost = models.BigIntegerField(default=0)            # 광고비(총비용)
    conversions = models.IntegerField(default=0)        # 총전환수
    conv_amount = models.BigIntegerField(default=0)     # 총전환금액(광고 기여 매출)
    collected_at = models.DateTimeField()

    class Meta:
        db_table = 'st11_product_daily'
        ordering = ['-stat_date']
        constraints = [
            models.UniqueConstraint(fields=['eleven_id', 'product_no', 'stat_date'],
                                    name='uniq_eleven_product_day'),
        ]
        indexes = [
            models.Index(fields=['eleven_id', 'stat_date']),
            models.Index(fields=['stat_date']),
            # 전체계정 월 GROUP BY(eleven_id, product_no) 커버링 — stat_date leftmost로 월범위만 스캔
            models.Index(fields=['stat_date', 'eleven_id', 'product_no', 'cost', 'conv_amount'],
                         name='st11pd_month_cover_idx'),
        ]


class St11KeywordDaily(models.Model):
    """11번가 adoffice 일별 (상품×키워드) 광고지표 — 키워드별 ROAS용 누적.
    멱등성은 (계정,기간) 교체저장으로 보장(키워드 문자열은 길어 unique 미사용)."""
    eleven_id = models.CharField(max_length=50)
    product_no = models.CharField(max_length=50)
    keyword = models.CharField(max_length=255)
    stat_date = models.DateField()
    campaign_name = models.CharField(max_length=255, blank=True)
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    cost = models.BigIntegerField(default=0)
    conversions = models.IntegerField(default=0)
    conv_amount = models.BigIntegerField(default=0)
    collected_at = models.DateTimeField()

    class Meta:
        db_table = 'st11_keyword_daily'
        ordering = ['-stat_date']
        indexes = [
            models.Index(fields=['eleven_id', 'stat_date']),
            models.Index(fields=['stat_date']),
        ]


class St11LossDeleted(models.Model):
    """적자상품 삭제완료 기록 — 비고에 '삭제완료'(파란색) 표시용."""
    eleven_id = models.CharField(max_length=50)
    product_no = models.CharField(max_length=50)
    seller_code = models.CharField(max_length=100, blank=True, default='')
    deleted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'st11_loss_deleted'
        unique_together = ('eleven_id', 'product_no')
        indexes = [models.Index(fields=['eleven_id', 'product_no'])]


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
    weekdays = models.JSONField(default=list, blank=True)        # ON 요일 [1=월 … 7=일], 빈값=매일
    off_weekdays = models.JSONField(default=list, blank=True)    # OFF 요일 [1=월 … 7=일], 빈값=매일
    include_cpc1 = models.BooleanField(default=False)            # True면 일반광고(일반그룹)도 함께 ON/OFF
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
    off_on_time = models.TimeField(null=True, blank=True)
    skip_holidays = models.BooleanField(default=True)
    selected_accounts = models.JSONField(default=list, blank=True)
    enabled_holidays = models.JSONField(default=list, blank=True)
    custom_holidays = models.JSONField(default=list, blank=True)
    weekdays = models.JSONField(default=list, blank=True)        # ON 요일 [1=월 … 7=일], 빈값=매일
    off_weekdays = models.JSONField(default=list, blank=True)    # OFF 요일 [1=월 … 7=일], 빈값=매일
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
    """SMS 수신 메시지 (OTP 인증 + smsApp 게이트웨이)"""
    csphone_number = models.CharField(max_length=20, blank=True)
    checkphone_number = models.CharField(max_length=20, blank=True)
    message = models.TextField(blank=True)
    msg_type = models.CharField(max_length=10, default='SMS')  # SMS / LMS / MMS
    receive_time = models.DateTimeField(null=True, blank=True)  # 단말기 수신 시각
    received_at = models.DateTimeField(auto_now_add=True)        # 서버 저장 시각
    setting_id = models.IntegerField(default=1)
    device_sms_id = models.BigIntegerField(null=True, blank=True, db_index=True)  # 폰 SMS DB의 _id (adb 폴러 dedup용)
    class Meta:
        db_table = 'received_sms_message'
        ordering = ['-received_at']


class SmsPhoneSetting(models.Model):
    """SMS 수신 전화번호 설정 (위젯 + smsApp /api/settings/ 공용)"""
    phone_number = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'sms_phone_settings'
        ordering = ['phone_number']


class SmsOutbox(models.Model):
    """SMS 발송 대기열 (서버 → smsApp)"""
    STATUS_CHOICES = [('pending', 'pending'), ('sent', 'sent'), ('failed', 'failed')]
    phone_number = models.CharField(max_length=20)
    message = models.TextField()
    sender_phone = models.CharField(max_length=20, blank=True)
    template_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    error_message = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        db_table = 'sms_outbox'
        ordering = ['-created_at']


class SmsDeviceHeartbeat(models.Model):
    """smsApp 디바이스 상태 (30초마다 heartbeat)"""
    phone_number = models.CharField(max_length=20, unique=True)
    app_version = models.CharField(max_length=20, blank=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'sms_device_heartbeat'


class SmsMessageImage(models.Model):
    """MMS 이미지 첨부"""
    message = models.ForeignKey('ReceivedSmsMessage', on_delete=models.CASCADE, related_name='images')
    filename = models.CharField(max_length=255, blank=True)
    filepath = models.CharField(max_length=500)
    content_type = models.CharField(max_length=50, blank=True)
    size = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'sms_message_image'


class ElevenMyProduct(models.Model):
    account = models.ForeignKey(CrawlerAccount, on_delete=models.CASCADE, related_name='eleven_my_products')
    product_no = models.BigIntegerField(db_index=True)
    product_name = models.CharField(max_length=500, blank=True, default='')
    sale_price = models.IntegerField(default=0)
    stock_quantity = models.IntegerField(default=0)
    status_type = models.CharField(max_length=20, blank=True, default='')
    seller_product_code = models.CharField(max_length=100, blank=True, default='')
    category_id = models.CharField(max_length=50, blank=True, default='')
    product_image_url = models.TextField(blank=True, default='')
    synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # 구매원가 = 예비상품(ownerclan) 마켓가 (seller_product_code=product_code 매칭). 정렬용 비정규화 컬럼.
    purchase_cost = models.IntegerField(null=True, blank=True, db_index=True)
    # 차이 = 판매가 - 구매원가 (DB STORED 생성컬럼 → 인덱스 정렬). purchase_cost 갱신 시 자동 재계산.
    cost_diff = models.GeneratedField(
        expression=models.F('sale_price') - models.F('purchase_cost'),
        output_field=models.IntegerField(),
        db_persist=True,
        db_index=True,
    )
    class Meta:
        db_table = 'eleven_my_product'
        unique_together = [('account', 'product_no')]
        indexes = [
            models.Index(fields=['account', 'status_type']),
            models.Index(fields=['synced_at']),
            # 구매원가 incremental 갱신(예비상품 코드 매칭) + 코드 검색용
            models.Index(fields=['seller_product_code']),
        ]


class GmarketCostHistory(models.Model):
    """지마켓/옥션(ESM) 판매예치금 거래내역 — 광고비(CPC 광고구매) 포함.
    ESM 판매예치금(현금성)은 통합이라 IacSellBalanceUseListSearch가 통합 거래내역 반환.
    중복방지: (seller_id, use_date, seq) 유니크 + 수집 시 기간 삭제후 재삽입(멱등)."""
    seller_id = models.CharField(max_length=50, db_index=True)   # 판매자ID(계정 login_id) — 복수아이디면 서브 id별
    market = models.CharField(max_length=10, blank=True, default='', db_index=True)  # gmarket/auction (판매예치금 출처 분리)
    use_date = models.DateField(db_index=True)                    # 거래일(UseDate, 날짜)
    traded_at = models.DateTimeField(null=True, blank=True)       # 거래일시(시:분:초까지 — 시간대별 분석용)
    seq = models.IntegerField(default=0)                          # 같은 날짜 내 순번
    use_type = models.CharField(max_length=20, blank=True, default='')       # 차감/적립
    transaction_type = models.CharField(max_length=20, blank=True, default='')  # CPC광고/예치금전환/정산/기타
    comment = models.CharField(max_length=255, blank=True, default='')       # 원본 거래항목
    amount = models.BigIntegerField(default=0)                    # 금액(음수=차감)
    related_no = models.CharField(max_length=50, blank=True, default='')     # 주문/배송/결제번호 등
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gmarket_cost_history'
        # market 포함 — 같은 계정의 지마켓/옥션 거래를 분리 저장(복수아이디 id별 + 플랫폼별)
        unique_together = [('seller_id', 'market', 'use_date', 'seq')]
        ordering = ['-use_date', 'seq']
        indexes = [
            models.Index(fields=['seller_id', 'use_date']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['market', 'use_date']),
        ]


class GmarketAdGroupPerf(models.Model):
    """지마켓 CPC 광고그룹별 성과 — ESM 광고센터(ad.esmplus.com/cpc/bidmng/bidmanagement)
    #tbGroupAdStateList(일반)/#tbSmartGroupAdStateList(간편) 그리드에서 수집.
    하루 1행/그룹(stat_date 기준, 멱등 재삽입)."""
    AD_TYPES = [('normal', '일반광고'), ('smart', '간편광고')]
    gmarket_id = models.CharField(max_length=50, db_index=True)   # 계정 login_id
    ad_type = models.CharField(max_length=10, choices=AD_TYPES, default='normal')
    stat_date = models.DateField(db_index=True)                   # 수집 기준일(KST)
    ad_group_name = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(max_length=20, blank=True, default='')   # ON/OFF 등
    ad_on = models.IntegerField(default=0)                        # 광고수 ON
    ad_off = models.IntegerField(default=0)                       # 광고수 OFF
    avg_rank = models.CharField(max_length=20, blank=True, default='')  # 평균순위지표(텍스트)
    impressions = models.BigIntegerField(default=0)              # 노출수
    clicks = models.BigIntegerField(default=0)                    # 클릭수
    ctr = models.DecimalField(max_digits=8, decimal_places=2, default=0)   # 클릭율(%)
    avg_click_cost = models.BigIntegerField(default=0)           # 평균클릭비용(VAT포함)
    total_cost = models.BigIntegerField(default=0)               # 총비용=광고비(VAT포함)
    daily_budget = models.CharField(max_length=50, blank=True, default='')  # 1일 허용예산(텍스트)
    product_count = models.CharField(max_length=50, blank=True, default='') # 상품 수(예: 'G마켓 49 / A옥션 0')
    collected_at = models.DateTimeField()

    class Meta:
        db_table = 'gmarket_adgroup_perf'
        unique_together = [('gmarket_id', 'ad_type', 'stat_date', 'ad_group_name')]
        ordering = ['-stat_date', 'gmarket_id']
        indexes = [
            models.Index(fields=['gmarket_id', 'stat_date']),
            models.Index(fields=['collected_at']),
        ]


class GmarketProductAdCost(models.Model):
    """지마켓 상품별 광고비 — 광고센터 리포트(CPC: cpc/report/groupReport,
    AI매출업: Remarketing/Report/GroupReport)의 '상품별' 다운로드 적재.
    월별 누적: (login_id, ad_type, product_no, year, month) 유니크 → 수집 시
    해당 (login_id, ad_type, year, month) 범위 삭제 후 재삽입(멱등, 중복방지)."""
    AD_TYPES = [('cpc', 'CPC'), ('ai', 'AI매출업')]
    login_id = models.CharField(max_length=50, db_index=True)   # 크롤 로그인 계정
    seller_id = models.CharField(max_length=50, blank=True, default='')  # 실제 판매자ID(AI=판매자ID열, CPC=리포트셀러)
    ad_type = models.CharField(max_length=4, choices=AD_TYPES, db_index=True)
    product_no = models.CharField(max_length=50, db_index=True)  # 상품번호
    year = models.IntegerField()
    month = models.IntegerField()
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    group_name = models.CharField(max_length=255, blank=True, default='')
    site = models.CharField(max_length=10, blank=True, default='')   # G마켓/옥션 (CPC)
    impressions = models.BigIntegerField(default=0)
    clicks = models.BigIntegerField(default=0)
    avg_click_cost = models.BigIntegerField(default=0)
    cost = models.BigIntegerField(default=0)            # 총비용=광고비(VAT포함)
    orders = models.IntegerField(default=0)             # 구매수(또는 주문수)
    conv_amount = models.BigIntegerField(default=0)     # 구매금액(광고기여 매출)
    conv_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0)   # 전환율(%)
    roas = models.DecimalField(max_digits=12, decimal_places=2, default=0)        # 광고수익률(%) 리포트값
    collected_at = models.DateTimeField()

    class Meta:
        db_table = 'gmarket_product_adcost'
        unique_together = [('login_id', 'ad_type', 'product_no', 'year', 'month')]
        ordering = ['-year', '-month', 'login_id', '-cost']
        indexes = [
            models.Index(fields=['login_id', 'ad_type', 'year', 'month']),
            models.Index(fields=['product_no']),
            models.Index(fields=['year', 'month', 'ad_type']),
        ]


class GmarketKeywordReport(models.Model):
    """지마켓 CPC 광고 키워드별 실적 — 광고센터 cpc/report/groupReport '키워드' 탭에서
    상품번호별 검색(#searchText)으로 키워드 행(#spanKeywordSearchData) 추출.
    월별 누적: (login_id, product_no, keyword, year, month) 유니크 →
    수집 시 (login_id, product_no, year, month) 범위 삭제 후 재삽입(멱등, 중복방지)."""
    login_id = models.CharField(max_length=50, db_index=True)
    seller_id = models.CharField(max_length=50, blank=True, default='')
    product_no = models.CharField(max_length=50, db_index=True)
    keyword = models.CharField(max_length=255)
    year = models.IntegerField()
    month = models.IntegerField()
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    impressions = models.BigIntegerField(default=0)
    clicks = models.BigIntegerField(default=0)
    click_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0)   # 클릭율(%)
    avg_rank = models.DecimalField(max_digits=8, decimal_places=2, default=0)     # 평균노출순위
    avg_click_cost = models.BigIntegerField(default=0)                            # 평균클릭비용
    cost = models.BigIntegerField(default=0)            # 총비용=광고비
    orders = models.IntegerField(default=0)             # 구매수
    conv_amount = models.BigIntegerField(default=0)     # 구매금액
    conv_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0)   # 전환율(%)
    roas = models.DecimalField(max_digits=12, decimal_places=2, default=0)        # 광고수익률(%)
    collected_at = models.DateTimeField()

    class Meta:
        db_table = 'gmarket_keyword_report'
        unique_together = [('login_id', 'product_no', 'keyword', 'year', 'month')]
        ordering = ['-year', '-month', 'login_id', '-cost']
        indexes = [
            models.Index(fields=['login_id', 'year', 'month']),
            models.Index(fields=['product_no']),
            models.Index(fields=['year', 'month']),
        ]


class GmarketMyProduct(models.Model):
    """지마켓/옥션(ESM) 나의 상품 — ESM item list(item.esmplus.com) 수집분.
    누적관리 + 상품번호 기준 중복제거: (account, market, product_no) 유니크 → upsert."""
    account = models.ForeignKey(CrawlerAccount, on_delete=models.CASCADE, related_name='gmarket_my_products')
    market = models.CharField(max_length=10, default='gmarket')          # gmarket | auction
    product_no = models.CharField(max_length=50, db_index=True)          # 상품번호(ESM 상품코드)
    product_name = models.CharField(max_length=500, blank=True, default='')
    sale_price = models.IntegerField(default=0)
    stock_quantity = models.IntegerField(default=0)
    status_type = models.CharField(max_length=20, blank=True, default='')   # 판매중/판매중지/품절 등
    seller_product_code = models.CharField(max_length=100, blank=True, default='')  # 판매자관리코드
    category_code = models.CharField(max_length=50, blank=True, default='')
    product_image_url = models.TextField(blank=True, default='')
    synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'gmarket_my_product'
        unique_together = [('account', 'market', 'product_no')]   # 상품번호 기준 중복제거
        indexes = [
            models.Index(fields=['account', 'status_type']),
            models.Index(fields=['product_no']),
            models.Index(fields=['synced_at']),
            # 중복제외(dedup) GROUP BY(account, seller_product_code) Min(id) 커버링
            models.Index(fields=['account', 'seller_product_code', 'id'],
                         name='gmkt_my_dedup_idx'),
        ]


class ElevenSellerOfficeStat(models.Model):
    """11번가 셀러오피스 메인 페이지에서 수집한 계정 현황 스냅샷"""
    account = models.ForeignKey(CrawlerAccount, on_delete=models.CASCADE, related_name='office_stats')
    cash = models.IntegerField(default=0)
    point = models.IntegerField(default=0)
    ad_balance = models.IntegerField(default=0)
    product_limit = models.IntegerField(default=0)
    products = models.IntegerField(default=0)
    banned = models.IntegerField(default=0)
    available = models.IntegerField(default=0)
    overdue = models.IntegerField(default=0)
    undelivered = models.IntegerField(default=0)
    draft = models.IntegerField(default=0)
    fulfillment = models.CharField(max_length=50, blank=True, default='')
    shipping = models.CharField(max_length=50, blank=True, default='')
    inquiry = models.CharField(max_length=50, blank=True, default='')
    error = models.TextField(blank=True, default='')
    collected_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'eleven_seller_office_stat'
        indexes = [models.Index(fields=['account', '-collected_at'])]
        ordering = ['-collected_at']


# ─────────────────────────────────────────────────────────────
# 세무(부가세/VAT) 모듈 — 마켓별 부가세신고내역 수집 + 사업자별 집계
# ─────────────────────────────────────────────────────────────
class TaxBusiness(models.Model):
    """사업자 (부가세 신고 단위)"""
    code = models.CharField(max_length=40, unique=True)        # 내부 코드
    name_short = models.CharField(max_length=100)              # 약칭
    name_official = models.CharField(max_length=200, blank=True, default='')  # 정식 상호
    biz_reg_no = models.CharField(max_length=20, blank=True, default='')      # 사업자등록번호
    biz_type = models.CharField(max_length=10, default='개인', choices=[('개인', '개인'), ('법인', '법인')])
    report_cycle = models.CharField(max_length=10, default='월', choices=[('월', '월'), ('분기', '분기')])
    vat_number = models.CharField(max_length=40, blank=True, default='')
    memo = models.CharField(max_length=300, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tax_business'
        ordering = ['biz_type', 'name_short']


class TaxAccountMap(models.Model):
    """마켓 로그인계정(login_id) ↔ 사업자 매핑"""
    business = models.ForeignKey(TaxBusiness, on_delete=models.SET_NULL, null=True, blank=True, related_name='accounts')
    platform = models.CharField(max_length=20, default='11st')
    login_id = models.CharField(max_length=100)
    account_name = models.CharField(max_length=100, blank=True, default='')
    memo = models.CharField(max_length=200, blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'tax_account_map'
        unique_together = [('platform', 'login_id')]


class TaxVatMonthly(models.Model):
    """마켓·계정·월별 부가세신고내역(매출)"""
    business = models.ForeignKey(TaxBusiness, on_delete=models.SET_NULL, null=True, blank=True, related_name='vat_monthly')
    platform = models.CharField(max_length=20, default='11st')
    login_id = models.CharField(max_length=100)
    seller_name = models.CharField(max_length=100, blank=True, default='')
    year = models.IntegerField()
    month = models.IntegerField()
    taxable_sales = models.BigIntegerField(default=0)     # 과세매출
    tax_free_sales = models.BigIntegerField(default=0)    # 면세매출
    zero_rate_sales = models.BigIntegerField(default=0)   # 영세매출
    credit_card = models.BigIntegerField(default=0)       # 신용카드
    cash_receipt = models.BigIntegerField(default=0)      # 현금영수증
    expense_proof = models.BigIntegerField(default=0)     # 지출증빙
    mobile = models.BigIntegerField(default=0)            # 휴대폰
    etc_amount = models.BigIntegerField(default=0)        # 기타
    extra_fee = models.BigIntegerField(default=0)         # 부가수수료
    collected_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tax_vat_monthly'
        unique_together = [('platform', 'login_id', 'year', 'month')]
        ordering = ['-year', '-month']


class TaxPurchase(models.Model):
    """매입(광고비/수수료 세금계산서) — 매입세액 공제용"""
    business = models.ForeignKey(TaxBusiness, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchases')
    platform = models.CharField(max_length=20, default='11st')
    login_id = models.CharField(max_length=100)
    year = models.IntegerField()
    month = models.IntegerField()
    source = models.CharField(max_length=20, default='ad')   # ad(광고비)/fee(수수료)
    supply_amount = models.BigIntegerField(default=0)        # 공급가액
    vat_amount = models.BigIntegerField(default=0)           # 부가세액
    collected_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tax_purchase'
        unique_together = [('platform', 'login_id', 'year', 'month', 'source')]
        ordering = ['-year', '-month']


class GmarketLossDeleted(models.Model):
    """지마켓 적자상품 삭제완료 기록 — 비고에 '삭제완료'(파란색) 표시용. [[St11LossDeleted]] 대응."""
    login_id = models.CharField(max_length=50)
    product_no = models.CharField(max_length=50)
    seller_code = models.CharField(max_length=100, blank=True, default='')
    deleted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gmarket_loss_deleted'
        unique_together = ('login_id', 'product_no')
        indexes = [models.Index(fields=['login_id', 'product_no'])]


class ProductCodeArchive(models.Model):
    """상품번호 → 판매자코드 영구 보존고(append/upsert). 마켓에서 삭제돼도 코드를 보관.
    출처: 매일 카탈로그 스냅샷(crawl) / 적자엑셀 적재(excel) / 다운로드 시점(download)."""
    platform = models.CharField(max_length=20)          # '11st' / 'gmarket'
    login_id = models.CharField(max_length=100, blank=True, default='')
    product_no = models.CharField(max_length=50, db_index=True)
    seller_code = models.CharField(max_length=100, blank=True, default='')
    product_name = models.CharField(max_length=500, blank=True, default='')
    source = models.CharField(max_length=30, blank=True, default='')
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'product_code_archive'
        unique_together = ('platform', 'product_no')
        indexes = [models.Index(fields=['platform', 'product_no']),
                   models.Index(fields=['seller_code'])]
