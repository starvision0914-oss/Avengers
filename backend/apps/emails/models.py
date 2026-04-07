from django.db import models


class EmailAccount(models.Model):
    email_address = models.EmailField(unique=True)
    display_name = models.CharField(max_length=200, blank=True)
    provider = models.CharField(max_length=20, default='custom',
                                choices=[('naver', '네이버'), ('gmail', 'Gmail'), ('daum', '다음'), ('custom', '직접설정')])
    imap_host = models.CharField(max_length=200)
    imap_port = models.IntegerField(default=993)
    smtp_host = models.CharField(max_length=200)
    smtp_port = models.IntegerField(default=587)
    smtp_use_tls = models.BooleanField(default=True)
    username = models.CharField(max_length=200)
    password = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'email_accounts'


class EmailMessage(models.Model):
    account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE, related_name='messages')
    message_id = models.CharField(max_length=500, blank=True)
    uid = models.IntegerField(null=True, blank=True)
    folder = models.CharField(max_length=100, default='INBOX')
    subject = models.CharField(max_length=1000, blank=True)
    from_addr = models.CharField(max_length=300, blank=True)
    from_name = models.CharField(max_length=200, blank=True)
    to_addrs = models.JSONField(default=list)
    cc_addrs = models.JSONField(default=list, blank=True)
    date = models.DateTimeField(null=True, blank=True)
    snippet = models.CharField(max_length=500, blank=True)
    body_text = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    has_attachment = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    is_starred = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'email_messages'
        ordering = ['-date']


class EmailAttachment(models.Model):
    message = models.ForeignKey(EmailMessage, on_delete=models.CASCADE, related_name='attachments')
    filename = models.CharField(max_length=500)
    content_type = models.CharField(max_length=100, blank=True)
    size = models.IntegerField(default=0)
    file_path = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'email_attachments'


class EmailLabel(models.Model):
    name = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=20, default='#6B7280')
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'email_labels'


class EmailMessageLabel(models.Model):
    message = models.ForeignKey(EmailMessage, on_delete=models.CASCADE, related_name='labels')
    label = models.ForeignKey(EmailLabel, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'email_message_labels'
        unique_together = ['message', 'label']
