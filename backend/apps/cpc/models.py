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
