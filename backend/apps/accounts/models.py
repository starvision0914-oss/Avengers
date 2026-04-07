from django.db import models
from django.conf import settings


class SellerAccount(models.Model):
    seller_id = models.CharField(max_length=100, unique=True)
    seller_name = models.CharField(max_length=200)
    platform = models.CharField(max_length=50, default='gmarket',
                                choices=[('gmarket', 'Gmarket'), ('auction', 'Auction'), ('11st', '11번가'), ('coupang', '쿠팡'), ('smartstore', '스마트스토어')])
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    memo = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'seller_accounts'
        ordering = ['display_order', 'seller_id']
