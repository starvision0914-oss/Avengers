from rest_framework import viewsets
from .models import SellerAccount
from .serializers import SellerAccountSerializer


class SellerAccountViewSet(viewsets.ModelViewSet):
    queryset = SellerAccount.objects.all()
    serializer_class = SellerAccountSerializer
    search_fields = ['seller_id', 'seller_name']
    ordering_fields = ['display_order', 'seller_id', 'created_at']
