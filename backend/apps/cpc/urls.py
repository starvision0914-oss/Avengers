from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CPCDailyCostViewSet, CPCDepositViewSet, CPCTransactionViewSet,
    CPCSummaryView, CPCChartView,
    CrawlerAccountViewSet, CrawlerLogViewSet, GmarketSnapshotViewSet,
    ElevenCostViewSet, GmarketGradeViewSet, ElevenGradeViewSet,
    GmarketSummaryView, ElevenSummaryView,
    GmarketAiViewSet, St11CampaignViewSet,
    CrawlTriggerView,
)

router = DefaultRouter()
router.register(r'daily', CPCDailyCostViewSet)
router.register(r'deposits', CPCDepositViewSet)
router.register(r'transactions', CPCTransactionViewSet)
router.register(r'crawler/accounts', CrawlerAccountViewSet)
router.register(r'crawler/logs', CrawlerLogViewSet, basename='crawlerlog')
router.register(r'gmarket-snapshots', GmarketSnapshotViewSet, basename='gmarketsnapshot')
router.register(r'eleven-costs', ElevenCostViewSet, basename='elevencost')
router.register(r'gmarket-grades', GmarketGradeViewSet)
router.register(r'eleven-grades', ElevenGradeViewSet)
router.register(r'gmarket-ai', GmarketAiViewSet)
router.register(r'st11-campaigns', St11CampaignViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('summary/', CPCSummaryView.as_view()),
    path('chart/', CPCChartView.as_view()),
    path('crawler/trigger/', CrawlTriggerView.as_view()),
    path('gmarket-summary/', GmarketSummaryView.as_view()),
    path('eleven-summary/', ElevenSummaryView.as_view()),
]
