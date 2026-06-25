from django.db import models


class NaverBlogSetting(models.Model):
    """전역 설정 (싱글톤)"""
    gemini_api_key = models.CharField(max_length=200, blank=True, default='')
    naver_client_id = models.CharField(max_length=100, blank=True, default='')
    naver_client_secret = models.CharField(max_length=100, blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'naver_blog_setting'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class NaverBlogAccount(models.Model):
    login_id = models.CharField(max_length=100)
    login_pw = models.CharField(max_length=200, blank=True, default='')
    blog_id = models.CharField(max_length=100, blank=True, default='')
    display_name = models.CharField(max_length=100, blank=True, default='')
    memo = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=99)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'naver_blog_account'
        ordering = ['display_order']

    def __str__(self):
        return self.display_name or self.login_id


class NaverKeyword(models.Model):
    keyword = models.CharField(max_length=200, unique=True)
    category = models.CharField(max_length=100, blank=True, default='')
    # 검색량 (키워드마스터 or 데이터랩 추정)
    search_pc = models.IntegerField(default=0)
    search_mobile = models.IntegerField(default=0)
    search_total = models.IntegerField(default=0)
    # 경쟁도 (블로그 발행 수)
    blog_count = models.IntegerField(default=0)
    competition = models.CharField(max_length=20, blank=True, default='')  # low/mid/high
    # 트렌드 (데이터랩 ratio 0~100, JSON)
    trend_data = models.JSONField(null=True, blank=True)
    trend_period = models.CharField(max_length=20, blank=True, default='')
    # 상태
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)  # 높을수록 우선 포스팅
    last_collected = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'naver_keyword'
        ordering = ['-priority', '-search_total']

    def __str__(self):
        return self.keyword

    @property
    def search_total_calc(self):
        return self.search_pc + self.search_mobile


class NaverBlogPost(models.Model):
    STATUS_CHOICES = [
        ('draft', '초안'),
        ('ready', '발행대기'),
        ('published', '발행완료'),
        ('failed', '발행실패'),
    ]

    account = models.ForeignKey(NaverBlogAccount, null=True, blank=True, on_delete=models.SET_NULL, related_name='posts')
    keyword = models.ForeignKey(NaverKeyword, null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=500)
    content = models.TextField(blank=True, default='')
    content_html = models.TextField(blank=True, default='')
    tags = models.CharField(max_length=500, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    published_url = models.CharField(max_length=500, blank=True, default='')
    published_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'naver_blog_post'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class NaverBlogPostImage(models.Model):
    post = models.ForeignKey(NaverBlogPost, on_delete=models.CASCADE, related_name='images')
    image_path = models.CharField(max_length=500)
    source_url = models.CharField(max_length=500, blank=True, default='')
    order = models.IntegerField(default=0)

    class Meta:
        db_table = 'naver_blog_post_image'
        ordering = ['order']
