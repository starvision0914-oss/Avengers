from rest_framework import serializers
from .models import SalesRecord, SalesUploadLog


class SalesRecordSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source='seller.seller_name', read_only=True)

    class Meta:
        model = SalesRecord
        fields = '__all__'


class SalesUploadLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesUploadLog
        fields = '__all__'
