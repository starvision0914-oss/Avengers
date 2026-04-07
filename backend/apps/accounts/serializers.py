from rest_framework import serializers
from .models import SellerAccount


class SellerAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = SellerAccount
        fields = '__all__'
