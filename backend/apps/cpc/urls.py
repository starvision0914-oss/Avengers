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
    CpcAdStatusViewSet, Cpc2ScheduleViewSet, Cpc2HistoryViewSet,
    AiScheduleViewSet, TelegramConfigViewSet, TelegramRecipientViewSet,
    SellerGroupViewSet, TelegramSendView, Cpc2ControlView,
    CronScheduleViewSet, CronApplyView, AccountUnblockView,
    AiControlView, SmsReceiveView, SmsOtpTestView,
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
router.register(r'cpc-status', CpcAdStatusViewSet)
router.register(r'cpc2-schedule', Cpc2ScheduleViewSet)
router.register(r'cpc2-history', Cpc2HistoryViewSet, basename='cpc2history')
router.register(r'ai-schedule', AiScheduleViewSet)
router.register(r'telegram/config', TelegramConfigViewSet)
router.register(r'telegram/recipients', TelegramRecipientViewSet)
router.register(r'seller-groups', SellerGroupViewSet)
router.register(r'cron-schedules', CronScheduleViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('summary/', CPCSummaryView.as_view()),
    path('chart/', CPCChartView.as_view()),
    path('crawler/trigger/', CrawlTriggerView.as_view()),
    path('gmarket-summary/', GmarketSummaryView.as_view()),
    path('eleven-summary/', ElevenSummaryView.as_view()),
    path('telegram/send/', TelegramSendView.as_view()),
    path('cpc2/control/', Cpc2ControlView.as_view()),
    path('cron/apply/', CronApplyView.as_view()),
    path('ai/control/', AiControlView.as_view()),
    path('sms/receive/', SmsReceiveView.as_view()),
    path('sms/otp-test/', SmsOtpTestView.as_view()),
    path('crawler/unblock/', AccountUnblockView.as_view()),
]
