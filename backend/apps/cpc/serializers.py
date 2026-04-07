from rest_framework import serializers
from .models import CPCDailyCost, CPCDeposit, CPCTransaction


class CPCDailyCostSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source='seller.seller_name', read_only=True)
    seller_id_display = serializers.CharField(source='seller.seller_id', read_only=True)

    class Meta:
        model = CPCDailyCost
        fields = '__all__'


class CPCDepositSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source='seller.seller_name', read_only=True)

    class Meta:
        model = CPCDeposit
        fields = '__all__'


class CPCTransactionSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source='seller.seller_name', read_only=True)

    class Meta:
        model = CPCTransaction
        fields = '__all__'
