"""
스피드고 파이프라인 모델 — 도매매 마이박스 → 카테고리 매칭 → 마켓 등록 흐름.
"""
from django.db import models


STATUS_CHOICES = [
    ('새로담김',       '새로 담김'),         # 도매매 마이박스에서 막 수집
    ('이름가공완료',   '상품명 가공 완료'),  # (이번 MVP에선 미사용 - 원본 이름 유지)
    ('카테고리매칭',   '카테고리 매칭 완료'),
    ('등록준비',       '마켓 등록 준비'),
    ('등록완료',       '마켓 등록 완료'),
    ('운영중',         '운영 중'),
    ('보류',           '보류'),
    ('삭제',           '삭제됨'),
]


class SpeedgoItem(models.Model):
    """도매매 마이박스에서 수집된 상품 단위."""
    id = models.AutoField(primary_key=True)
    domemea_no = models.CharField(max_length=50, unique=True, db_index=True,
                                  help_text='도매매 상품번호')
    original_name = models.CharField(max_length=500,
                                     help_text='도매매 원본 상품명 (이번 MVP는 그대로 사용)')
    processed_name = models.CharField(max_length=500, blank=True, default='',
                                      help_text='가공된 상품명 (현재 비어있음 — 추후 LLM 적용)')

    wholesale_price = models.IntegerField(default=0)
    shipping_fee = models.IntegerField(default=0)
    supplier = models.CharField(max_length=100, blank=True, default='')
    main_image_url = models.TextField(blank=True, default='')
    detail_url = models.TextField(blank=True, default='')

    # 카테고리 매칭 결과
    naver_category_path = models.CharField(max_length=300, blank=True, default='',
                                           help_text='네이버 1위 상품 카테고리 경로')
    naver_top_product_url = models.TextField(blank=True, default='')
    naver_matched_at = models.DateTimeField(null=True, blank=True)

    # 마켓별 카테고리 매핑 (예: {"11st": "1001234", "gmarket": "200-456", ...})
    market_categories = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='새로담김')
    note = models.CharField(max_length=300, blank=True, default='')

    collected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'speedgo_item'
        ordering = ['-collected_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['naver_category_path']),
        ]

    def display_name(self):
        """가공된 이름이 있으면 그것, 없으면 원본."""
        return self.processed_name or self.original_name


class CategoryMapping(models.Model):
    """네이버 카테고리 → 각 마켓 카테고리 ID 매핑.
    네이버 카테고리 경로(예: 'a > b > c')를 키로, 마켓별 ID 저장."""
    id = models.AutoField(primary_key=True)
    naver_path = models.CharField(max_length=300, db_index=True)
    market = models.CharField(max_length=20)  # '11st' / 'gmarket' / 'coupang' / 'smartstore'
    market_category_id = models.CharField(max_length=50)
    market_category_path = models.CharField(max_length=300, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'speedgo_category_mapping'
        unique_together = [('naver_path', 'market')]


class SpeedgoLog(models.Model):
    """파이프라인 작업 로그 (수집/매칭/등록 기록)."""
    id = models.AutoField(primary_key=True)
    item = models.ForeignKey(SpeedgoItem, on_delete=models.CASCADE,
                             null=True, blank=True, related_name='logs')
    stage = models.CharField(max_length=30)  # 'collect' / 'match_category' / 'register' / ...
    level = models.CharField(max_length=10, default='info')  # info/warn/error/success
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'speedgo_log'
        ordering = ['-created_at']
