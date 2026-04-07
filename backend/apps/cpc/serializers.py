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


from .models import CrawlerAccount, CrawlerLog, GmarketDepositSnapshot, ElevenCostHistory, GmarketSellerGrade, ElevenSellerGrade

class CrawlerAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrawlerAccount
        fields = '__all__'
        extra_kwargs = {'password_enc': {'write_only': True}}

class CrawlerLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrawlerLog
        fields = '__all__'

class GmarketDepositSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = GmarketDepositSnapshot
        fields = '__all__'

class ElevenCostHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ElevenCostHistory
        fields = '__all__'

class GmarketGradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GmarketSellerGrade
        fields = '__all__'

class ElevenGradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElevenSellerGrade
        fields = '__all__'
