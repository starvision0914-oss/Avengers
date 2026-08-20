from django.db import models


class LotteonAccount(models.Model):
    """롯데온 판매자센터 계정"""
    login_id = models.CharField(max_length=100, unique=True)
    login_pw = models.CharField(max_length=200, blank=True, default='')
    store_name = models.CharField(max_length=100, blank=True, default='')
    seller_no = models.CharField(max_length=20, blank=True, default='', help_text='셀러ID (예: LO10163804)')
    is_active = models.BooleanField(default=True)
    cookie_data = models.TextField(blank=True, default='')
    cookie_saved_at = models.DateTimeField(null=True, blank=True)
    last_crawled_at = models.DateTimeField(null=True, blank=True)
    fail_count = models.IntegerField(default=0)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    # 롯데온 오픈API (판매자센터 > 판매자 정보 > OpenAPI관리에서 발급)
    api_key = models.CharField(max_length=200, blank=True, default='')
    api_key_expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'lotteon_account'
        ordering = ['display_order', 'id']

    def __str__(self):
        return f'{self.store_name or self.login_id}'

    @property
    def has_api_key(self):
        return bool(self.api_key)


class LotteonAdCost(models.Model):
    """롯데온 광고비 (광고주센터 ad.lotteon.com > 클릭광고 리포트 > 일자별 리포트 수집).
    raw_json: 응답 원본 보존 — 테스트 계정(광고집행 0원)에서 개발해 실제 필드명을 데이터로
    검증 못한 상태라, 필드 매핑이 틀렸을 경우 재크롤 없이 raw_json으로 재처리 가능하게 함."""
    account = models.ForeignKey(LotteonAccount, on_delete=models.CASCADE, related_name='ad_costs')
    date = models.DateField(db_index=True)
    ad_type = models.CharField(max_length=20, blank=True, default='')
    cost = models.BigIntegerField(default=0)
    click = models.IntegerField(default=0)
    impression = models.IntegerField(default=0)
    conversions = models.IntegerField(default=0)
    conversion_amount = models.BigIntegerField(default=0)
    raw_json = models.TextField(blank=True, default='')
    collected_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lotteon_ad_cost'
        unique_together = [('account', 'date', 'ad_type')]
        ordering = ['-date']
        indexes = [
            models.Index(fields=['account', 'date']),
        ]

    def __str__(self):
        return f'{self.account.login_id} {self.date} {self.ad_type}'


class LotteonProductAdCost(models.Model):
    """롯데온 상품별 광고비 (광고주센터 > 클릭광고 리포트 > 상품별 리포트, 일 단위로 수집).
    응답 필드명이 실측(광고집행 0원 계정)으로 검증되지 않아 raw_json에 원본 row를 통째로 보존.
    seller_item_no/product_name/cost 등은 최선 추정 매핑 — 실데이터 확보 시 raw_json 재처리로 보정 가능."""
    account = models.ForeignKey(LotteonAccount, on_delete=models.CASCADE, related_name='product_ad_costs')
    date = models.DateField(db_index=True)
    seller_item_no = models.CharField(max_length=50, blank=True, default='')
    product_name = models.CharField(max_length=500, blank=True, default='')
    category_name = models.CharField(max_length=200, blank=True, default='')
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    cost = models.BigIntegerField(default=0)
    conversions = models.IntegerField(default=0)
    conversion_amount = models.BigIntegerField(default=0)
    raw_json = models.TextField(blank=True, default='')
    collected_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lotteon_product_ad_cost'
        unique_together = [('account', 'date', 'seller_item_no')]
        ordering = ['-date']
        indexes = [
            models.Index(fields=['account', 'date']),
        ]

    def __str__(self):
        return f'{self.account.login_id} {self.date} {self.seller_item_no}'


class LotteonMyProduct(models.Model):
    """롯데온 나의 상품 — 판매자센터 상품관리 > 상품 조회/수정 내부 API(soapi selectProductList) 수집분."""
    account = models.ForeignKey(LotteonAccount, on_delete=models.CASCADE, related_name='products')
    pd_no = models.CharField(max_length=30, db_index=True, help_text='상품번호(spdNo/pdNo)')
    product_name = models.CharField(max_length=500, blank=True, default='')
    sale_price = models.IntegerField(default=0)
    status_code = models.CharField(max_length=20, blank=True, default='', help_text='slStatCd (SALE 등)')
    seller_product_code = models.CharField(max_length=100, blank=True, default='', help_text='epdNo(판매자내부상품번호) — 화면 그리드 컬럼과 대조 확인(2026-08-20). cmNo는 상품별 값이 아니라 거래처 그룹코드라 오매핑이었음')
    category_path = models.CharField(max_length=300, blank=True, default='', help_text='dcatNmPath')
    synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lotteon_my_product'
        unique_together = [('account', 'pd_no')]
        indexes = [
            models.Index(fields=['account', 'status_code']),
        ]

    def __str__(self):
        return f'{self.account.login_id} {self.pd_no} {self.product_name[:30]}'
