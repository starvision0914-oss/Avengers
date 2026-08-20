from django.db import models


# ai100 EXCEL_COL_MAP 기준 트래커블 필드 (55개)
TRACKABLE_FIELDS = [
    'seller_code1', 'seller_code2',
    'category_code', 'category_name', 'market_category',
    'product_name', 'market_product_name',
    'ownerclan_price', 'consumer_price', 'market_price',
    'shipping_fee', 'shipping_type', 'min_qty', 'max_qty',
    'company_notice', 'special_notice',
    'option1_name', 'option1_values', 'option2_name', 'option2_values',
    'combined_option', 'product_attribute', 'product_grade',
    'tax_type', 'compliance', 'age_restriction', 'return_possible',
    'image_large', 'image_medium', 'image_small',
    'manufacturer', 'brand', 'model_name', 'origin', 'keywords',
    'registered_at', 'modified_at',
    'header_text', 'detail_html',
    'notice_code', 'notice_category', 'notice_info', 'notice_html',
    'market_gmarket', 'market_auction', 'market_11st',
    'market_coupang', 'market_smartstore', 'market_promo', 'market_gift',
    'certification_type', 'certification_info',
    'return_fee', 'independent_option', 'combined_option_detail',
]

INT_FIELDS = {
    'ownerclan_price', 'consumer_price', 'market_price',
    'shipping_fee', 'min_qty', 'max_qty', 'return_fee',
}

DATETIME_FIELDS = {'registered_at', 'modified_at'}


class OwnerclanProduct(models.Model):
    product_code = models.CharField(max_length=64, unique=True)
    sale_status = models.SmallIntegerField(default=1)
    is_synced = models.SmallIntegerField(default=1)
    uploaded_at = models.DateTimeField(null=True, blank=True)
    synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    seller_code1 = models.TextField(blank=True, default='')
    seller_code2 = models.TextField(blank=True, default='')
    category_code = models.TextField(blank=True, default='')
    category_name = models.TextField(blank=True, default='')
    market_category = models.TextField(blank=True, default='')
    product_name = models.TextField(blank=True, default='')
    market_product_name = models.TextField(blank=True, default='')
    ownerclan_price = models.IntegerField(default=0)
    consumer_price = models.IntegerField(default=0)
    market_price = models.IntegerField(default=0)
    shipping_fee = models.IntegerField(default=0)
    shipping_type = models.TextField(blank=True, default='')
    min_qty = models.IntegerField(default=0)
    max_qty = models.IntegerField(default=0)
    company_notice = models.TextField(blank=True, default='')
    special_notice = models.TextField(blank=True, default='')
    option1_name = models.TextField(blank=True, default='')
    option1_values = models.TextField(blank=True, default='')
    option2_name = models.TextField(blank=True, default='')
    option2_values = models.TextField(blank=True, default='')
    combined_option = models.TextField(blank=True, default='')
    product_attribute = models.TextField(blank=True, default='')
    product_grade = models.TextField(blank=True, default='')
    tax_type = models.TextField(blank=True, default='')
    compliance = models.TextField(blank=True, default='')
    age_restriction = models.TextField(blank=True, default='')
    return_possible = models.TextField(blank=True, default='')
    image_large = models.TextField(blank=True, default='')
    image_medium = models.TextField(blank=True, default='')
    image_small = models.TextField(blank=True, default='')
    manufacturer = models.TextField(blank=True, default='')
    brand = models.TextField(blank=True, default='')
    model_name = models.TextField(blank=True, default='')
    origin = models.TextField(blank=True, default='')
    keywords = models.TextField(blank=True, default='')
    registered_at = models.DateTimeField(null=True, blank=True)
    modified_at = models.DateTimeField(null=True, blank=True)
    header_text = models.TextField(blank=True, default='')
    detail_html = models.TextField(blank=True, default='')
    notice_code = models.TextField(blank=True, default='')
    notice_category = models.TextField(blank=True, default='')
    notice_info = models.TextField(blank=True, default='')
    notice_html = models.TextField(blank=True, default='')
    market_gmarket = models.TextField(blank=True, default='')
    market_auction = models.TextField(blank=True, default='')
    market_11st = models.TextField(blank=True, default='')
    market_coupang = models.TextField(blank=True, default='')
    market_smartstore = models.TextField(blank=True, default='')
    market_promo = models.TextField(blank=True, default='')
    market_gift = models.TextField(blank=True, default='')
    certification_type = models.TextField(blank=True, default='')
    certification_info = models.TextField(blank=True, default='')
    return_fee = models.IntegerField(default=0)
    independent_option = models.TextField(blank=True, default='')
    combined_option_detail = models.TextField(blank=True, default='')

    orig_seller_code1 = models.TextField(blank=True, default='')
    orig_seller_code2 = models.TextField(blank=True, default='')
    orig_category_code = models.TextField(blank=True, default='')
    orig_category_name = models.TextField(blank=True, default='')
    orig_market_category = models.TextField(blank=True, default='')
    orig_product_name = models.TextField(blank=True, default='')
    orig_market_product_name = models.TextField(blank=True, default='')
    orig_ownerclan_price = models.IntegerField(default=0)
    orig_consumer_price = models.IntegerField(default=0)
    orig_market_price = models.IntegerField(default=0)
    orig_shipping_fee = models.IntegerField(default=0)
    orig_shipping_type = models.TextField(blank=True, default='')
    orig_min_qty = models.IntegerField(default=0)
    orig_max_qty = models.IntegerField(default=0)
    orig_company_notice = models.TextField(blank=True, default='')
    orig_special_notice = models.TextField(blank=True, default='')
    orig_option1_name = models.TextField(blank=True, default='')
    orig_option1_values = models.TextField(blank=True, default='')
    orig_option2_name = models.TextField(blank=True, default='')
    orig_option2_values = models.TextField(blank=True, default='')
    orig_combined_option = models.TextField(blank=True, default='')
    orig_product_attribute = models.TextField(blank=True, default='')
    orig_product_grade = models.TextField(blank=True, default='')
    orig_tax_type = models.TextField(blank=True, default='')
    orig_compliance = models.TextField(blank=True, default='')
    orig_age_restriction = models.TextField(blank=True, default='')
    orig_return_possible = models.TextField(blank=True, default='')
    orig_image_large = models.TextField(blank=True, default='')
    orig_image_medium = models.TextField(blank=True, default='')
    orig_image_small = models.TextField(blank=True, default='')
    orig_manufacturer = models.TextField(blank=True, default='')
    orig_brand = models.TextField(blank=True, default='')
    orig_model_name = models.TextField(blank=True, default='')
    orig_origin = models.TextField(blank=True, default='')
    orig_keywords = models.TextField(blank=True, default='')
    orig_registered_at = models.DateTimeField(null=True, blank=True)
    orig_modified_at = models.DateTimeField(null=True, blank=True)
    orig_header_text = models.TextField(blank=True, default='')
    orig_detail_html = models.TextField(blank=True, default='')
    orig_notice_code = models.TextField(blank=True, default='')
    orig_notice_category = models.TextField(blank=True, default='')
    orig_notice_info = models.TextField(blank=True, default='')
    orig_notice_html = models.TextField(blank=True, default='')
    orig_market_gmarket = models.TextField(blank=True, default='')
    orig_market_auction = models.TextField(blank=True, default='')
    orig_market_11st = models.TextField(blank=True, default='')
    orig_market_coupang = models.TextField(blank=True, default='')
    orig_market_smartstore = models.TextField(blank=True, default='')
    orig_market_promo = models.TextField(blank=True, default='')
    orig_market_gift = models.TextField(blank=True, default='')
    orig_certification_type = models.TextField(blank=True, default='')
    orig_certification_info = models.TextField(blank=True, default='')
    orig_return_fee = models.IntegerField(default=0)
    orig_independent_option = models.TextField(blank=True, default='')
    orig_combined_option_detail = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'ownerclan_product'
        verbose_name = '예비상품'
        verbose_name_plural = '예비상품'
        indexes = [
            models.Index(fields=['sale_status']),
            models.Index(fields=['is_synced']),
            models.Index(fields=['uploaded_at']),
        ]


def _build_processing_product():
    """OwnerclanProduct와 동일 스키마의 상품가공 모델을 동적 생성(필드 중복정의 회피)."""
    attrs = {
        '__module__': __name__,
        '__doc__': '상품가공 — 예비상품(/ownerclan)과 동일 구조의 독립 워크스페이스.',
        'product_code': models.CharField(max_length=64, unique=True),
        'sale_status': models.SmallIntegerField(default=1),
        'is_synced': models.SmallIntegerField(default=1),
        'uploaded_at': models.DateTimeField(null=True, blank=True),
        'synced_at': models.DateTimeField(null=True, blank=True),
        'created_at': models.DateTimeField(auto_now_add=True),
        'updated_at': models.DateTimeField(auto_now=True),
    }
    for _f in TRACKABLE_FIELDS:
        for _name in (_f, f'orig_{_f}'):
            if _f in INT_FIELDS:
                attrs[_name] = models.IntegerField(default=0)
            elif _f in DATETIME_FIELDS:
                attrs[_name] = models.DateTimeField(null=True, blank=True)
            else:
                attrs[_name] = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'processing_product'
        verbose_name = '상품가공'
        verbose_name_plural = '상품가공'
        indexes = [
            models.Index(fields=['sale_status']),
            models.Index(fields=['is_synced']),
            models.Index(fields=['uploaded_at']),
        ]
    attrs['Meta'] = Meta
    return type('ProcessingProduct', (models.Model,), attrs)


ProcessingProduct = _build_processing_product()


class MyProduct(models.Model):
    source_product_code = models.CharField(max_length=64, db_index=True)
    my_product_code = models.CharField(max_length=80, unique=True)
    is_modified = models.BooleanField(default=False)
    copied_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    seller_code1 = models.TextField(blank=True, default='')
    seller_code2 = models.TextField(blank=True, default='')
    category_code = models.TextField(blank=True, default='')
    category_name = models.TextField(blank=True, default='')
    market_category = models.TextField(blank=True, default='')
    product_name = models.TextField(blank=True, default='')
    market_product_name = models.TextField(blank=True, default='')
    ownerclan_price = models.IntegerField(default=0)
    consumer_price = models.IntegerField(default=0)
    market_price = models.IntegerField(default=0)
    shipping_fee = models.IntegerField(default=0)
    shipping_type = models.TextField(blank=True, default='')
    min_qty = models.IntegerField(default=0)
    max_qty = models.IntegerField(default=0)
    company_notice = models.TextField(blank=True, default='')
    special_notice = models.TextField(blank=True, default='')
    option1_name = models.TextField(blank=True, default='')
    option1_values = models.TextField(blank=True, default='')
    option2_name = models.TextField(blank=True, default='')
    option2_values = models.TextField(blank=True, default='')
    combined_option = models.TextField(blank=True, default='')
    product_attribute = models.TextField(blank=True, default='')
    product_grade = models.TextField(blank=True, default='')
    tax_type = models.TextField(blank=True, default='')
    compliance = models.TextField(blank=True, default='')
    age_restriction = models.TextField(blank=True, default='')
    return_possible = models.TextField(blank=True, default='')
    image_large = models.TextField(blank=True, default='')
    image_medium = models.TextField(blank=True, default='')
    image_small = models.TextField(blank=True, default='')
    manufacturer = models.TextField(blank=True, default='')
    brand = models.TextField(blank=True, default='')
    model_name = models.TextField(blank=True, default='')
    origin = models.TextField(blank=True, default='')
    keywords = models.TextField(blank=True, default='')
    registered_at = models.DateTimeField(null=True, blank=True)
    modified_at = models.DateTimeField(null=True, blank=True)
    header_text = models.TextField(blank=True, default='')
    detail_html = models.TextField(blank=True, default='')
    notice_code = models.TextField(blank=True, default='')
    notice_category = models.TextField(blank=True, default='')
    notice_info = models.TextField(blank=True, default='')
    notice_html = models.TextField(blank=True, default='')
    market_gmarket = models.TextField(blank=True, default='')
    market_auction = models.TextField(blank=True, default='')
    market_11st = models.TextField(blank=True, default='')
    market_coupang = models.TextField(blank=True, default='')
    market_smartstore = models.TextField(blank=True, default='')
    market_promo = models.TextField(blank=True, default='')
    market_gift = models.TextField(blank=True, default='')
    certification_type = models.TextField(blank=True, default='')
    certification_info = models.TextField(blank=True, default='')
    return_fee = models.IntegerField(default=0)
    independent_option = models.TextField(blank=True, default='')
    combined_option_detail = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'my_product'
        verbose_name = '나의 상품'
        verbose_name_plural = '나의 상품'
        indexes = [
            models.Index(fields=['source_product_code']),
            models.Index(fields=['is_modified']),
            models.Index(fields=['copied_at']),
        ]


class OwnerclanApiAccount(models.Model):
    """오너클랜 정식 API(GraphQL) 로그인 계정 — ownerclan.com 판매사 ID/PW와 동일."""
    login_id = models.CharField(max_length=100, unique=True)
    login_pw = models.CharField(max_length=200)
    token = models.TextField(blank=True, default='')
    token_expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_new_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    # 오너클랜 마이페이지(웹) 스크래핑 정보 — GraphQL API 범위 밖(계정 전용 UI 정보)
    balance = models.CharField(max_length=50, blank=True, default='')            # 오너클랜머니
    order_stats = models.JSONField(default=dict, blank=True)                     # 주문/배송조회 현황
    subscription_info = models.JSONField(default=dict, blank=True)               # 구독서비스
    lowest_price_quota = models.JSONField(default=dict, blank=True)              # 나만의 최저가 선점권
    info_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ownerclan_api_account'

    def __str__(self):
        return self.login_id


class OwnerclanLiveStatus(models.Model):
    """W코드(오너클랜 상품코드)별 오너클랜 실제 판매상태 캐시 — 가격데이터(OwnerclanProduct/예비상품)와 무관하게
    나의상품(지마켓/11번가/스마트스토어) 전체 W코드를 주5일(월~금) 순환으로 라이브 조회해 채운다.
    품절/미존재 여부만 확인하는 용도라 market_price 등 가격 필드는 없음."""
    product_code = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=20)   # available/soldout/unavailable/discontinued/NOT_FOUND
    checked_at = models.DateTimeField()

    class Meta:
        db_table = 'ownerclan_live_status'
        indexes = [models.Index(fields=['status']), models.Index(fields=['checked_at'])]

    def __str__(self):
        return f'{self.product_code}:{self.status}'


class OwnerclanTask(models.Model):
    task_type = models.CharField(max_length=30)
    status = models.CharField(max_length=10, default='pending')
    input_data = models.JSONField(default=dict)
    result_data = models.JSONField(default=dict, blank=True)
    pid = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ownerclan_task'
        indexes = [models.Index(fields=['task_type', 'status'])]
