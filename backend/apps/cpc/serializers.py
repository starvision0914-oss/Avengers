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

from .models import GmarketAiAdSummary, GmarketAiAdHistory, St11AdofficeCampaign, St11AiAdHistory

class GmarketAiSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = GmarketAiAdSummary
        fields = '__all__'

class GmarketAiHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = GmarketAiAdHistory
        fields = '__all__'

class St11CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = St11AdofficeCampaign
        fields = '__all__'

class St11AiHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = St11AiAdHistory
        fields = '__all__'

from .models import GmarketCpcAdStatus, Cpc2Schedule, Cpc2History, CppSchedule, CppBidHistory, AiSchedule, TelegramConfig, TelegramRecipient, SellerGroup

class CpcAdStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = GmarketCpcAdStatus
        fields = '__all__'

class Cpc2ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cpc2Schedule
        fields = '__all__'

class Cpc2HistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Cpc2History
        fields = '__all__'

class CppScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CppSchedule
        fields = '__all__'

class CppBidHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CppBidHistory
        fields = '__all__'

class AiScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AiSchedule
        fields = '__all__'

class TelegramConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramConfig
        fields = '__all__'

class TelegramRecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramRecipient
        fields = '__all__'

class SellerGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = SellerGroup
        fields = '__all__'
