from django.db import models


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


class KeywordProduct(models.Model):
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
        db_table = 'keyword_product'
        verbose_name = '키워드추출기'
        verbose_name_plural = '키워드추출기'
        indexes = [
            models.Index(fields=['sale_status']),
            models.Index(fields=['is_synced']),
            models.Index(fields=['uploaded_at']),
        ]


class KeywordTask(models.Model):
    task_type = models.CharField(max_length=30)
    status = models.CharField(max_length=10, default='pending')
    input_data = models.JSONField(default=dict)
    result_data = models.JSONField(default=dict, blank=True)
    pid = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'keyword_task'
        indexes = [models.Index(fields=['task_type', 'status'])]
