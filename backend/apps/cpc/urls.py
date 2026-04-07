from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CPCDailyCostViewSet, CPCDepositViewSet, CPCTransactionViewSet,
    CPCSummaryView, CPCChartView,
    CrawlerAccountViewSet, CrawlerLogViewSet, GmarketSnapshotViewSet,
    ElevenCostViewSet, GmarketGradeViewSet, ElevenGradeViewSet,
    CrawlTriggerView,
)

router = DefaultRouter()
router.register(r'daily', CPCDailyCostViewSet)
router.register(r'deposits', CPCDepositViewSet)
router.register(r'transactions', CPCTransactionViewSet)
router.register(r'crawler/accounts', CrawlerAccountViewSet)
router.register(r'crawler/logs', CrawlerLogViewSet, basename='crawlerlog')
router.register(r'gmarket-snapshots', GmarketSnapshotViewSet)
router.register(r'eleven-costs', ElevenCostViewSet)
router.register(r'gmarket-grades', GmarketGradeViewSet)
router.register(r'eleven-grades', ElevenGradeViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('summary/', CPCSummaryView.as_view()),
    path('chart/', CPCChartView.as_view()),
    path('crawler/trigger/', CrawlTriggerView.as_view()),
]
