from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CPCDailyCostViewSet, CPCDepositViewSet, CPCTransactionViewSet, CPCSummaryView, CPCChartView

router = DefaultRouter()
router.register(r'daily', CPCDailyCostViewSet)
router.register(r'deposits', CPCDepositViewSet)
router.register(r'transactions', CPCTransactionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('summary/', CPCSummaryView.as_view()),
    path('chart/', CPCChartView.as_view()),
]
