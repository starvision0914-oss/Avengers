from django.db import models


class TistoryAccount(models.Model):
    login_id = models.CharField(max_length=100, help_text='카카오계정 이메일 또는 티스토리 자체 로그인 ID')
    login_pw = models.CharField(max_length=200, blank=True, default='')
    blog_name = models.CharField(max_length=100, help_text='블로그 주소(예: myblog.tistory.com 의 myblog)')
    display_name = models.CharField(max_length=100, blank=True, default='')
    memo = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=99)
    cookie_data = models.TextField(blank=True, default='')
    cookie_saved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tistory_account'
        ordering = ['display_order']

    def __str__(self):
        return self.display_name or self.blog_name


class TistoryPost(models.Model):
    STATUS_CHOICES = [
        ('draft', '초안'),
        ('tistory_draft', '티스토리 임시저장'),
        ('published', '발행완료'),
        ('failed', '발행실패'),
    ]

    account = models.ForeignKey(TistoryAccount, null=True, blank=True, on_delete=models.SET_NULL, related_name='posts')
    title = models.CharField(max_length=500)
    content = models.TextField(blank=True, default='')
    tags = models.CharField(max_length=500, blank=True, default='')
    category = models.CharField(max_length=100, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    tistory_post_id = models.CharField(max_length=50, blank=True, default='')
    tistory_last_saved_title = models.CharField(max_length=500, blank=True, default='')
    published_url = models.CharField(max_length=500, blank=True, default='')
    published_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tistory_post'
        ordering = ['-created_at']

    def __str__(self):
        return self.title
