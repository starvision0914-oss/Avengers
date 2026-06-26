from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CPCDailyCostViewSet, CPCDepositViewSet, CPCTransactionViewSet,
    CPCSummaryView, CPCChartView,
    CrawlerAccountViewSet, CrawlerLogViewSet, GmarketSnapshotViewSet,
    ElevenCostViewSet, GmarketGradeViewSet, ElevenGradeViewSet,
    GmarketSummaryView, ElevenSummaryView, ProfitDashboardView, OverviewView, AllMallProfitView, ElevenAdKilllistView,
    TaxVatSummaryView, ElevenGradeLatestView,
    GmarketAiViewSet, GmarketAiHistoryViewSet, St11CampaignViewSet,
    CrawlTriggerView, SellerAutoLoginView,
    St11CostCrawlView, St11CrawlStopView, St11CrawlStatusView, ElevenRoasView, ElevenProductRoasView, ElevenKeywordRoasView,
    St11ProductDailyCrawlView, ElevenLossDeleteView, ElevenLossMarkDeletedView,
    CpcAdStatusViewSet, Cpc2ScheduleViewSet, Cpc2HistoryViewSet,
    AiScheduleViewSet, TelegramConfigViewSet, TelegramRecipientViewSet,
    SellerGroupViewSet, TelegramSendView, Cpc2ControlView,
    CronScheduleViewSet, CronApplyView, AccountUnblockView,
    AiControlView, GmarketControlStopView, GmarketControlStatusView, SmsReceiveView, SmsOtpTestView,
    St11AdStrategyCampaignsView, St11AdStrategyControlView, St11AdStrategyLogView,
    St11AdStrategyAccountsView, St11AdStrategyRunsView, St11AdStrategyScheduleView,
    SmsPhoneSettingView, SmsLatestView, AdDetailView,
    MmsReceiveView, SmsOutboxView, SmsOutboxResultView,
    SmsHeartbeatView, SmsChangeNumberView, SmsSettingsListView,
    SmsOutboxHistoryView, SmsDeviceListView,
    CrawlerAccountStatsView,
    CrawlerAccountExcelUploadView, CrawlerAccountExcelSampleView,
    ElevenMyProductSyncView, ElevenMyProductListView,
    GmarketMyProductListView, GmarketMyAccountsView, GmarketDashboardView, GmarketCrawlStatusView, GmarketRecrawlView, GmarketCostDetailView,
    GmarketAdDailyView, GmarketAdGroupView,
    ElevenMyProductDetailView, ElevenMyProductAccountSummaryView,
    ElevenMyProductDuplicateView, ElevenIntegratedSyncView,
    ElevenSyncStatusView, ElevenBlockClearView,
    BlockedAccountsView, GmarketTimeseriesView,
    GmarketProductRoasView, GmarketRoasAccountsView,
    GmarketLossProductsView, GmarketLossMarkDeletedView, GmarketLossDeleteView,
    GmarketKeywordCrawlView, GmarketKeywordUploadView, GmarketKeywordStatusView,
    GmarketKeywordCumulativeView, GmarketFocusTargetsView,
    ElevenAuthStatusView, ElevenVerifyOtpView,
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
router.register(r'ai-history', GmarketAiHistoryViewSet, basename='aihistory')
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
    path('all-mall-profit/', AllMallProfitView.as_view()),
    path('eleven-ad-killlist/', ElevenAdKilllistView.as_view()),
    path('crawler/trigger/', CrawlTriggerView.as_view()),
    path('crawler/eleven-cost/run/', St11CostCrawlView.as_view()),
    path('crawler/eleven-cost/stop/', St11CrawlStopView.as_view()),
    path('crawler/eleven-cost/status/', St11CrawlStatusView.as_view()),
    path('eleven-roas/', ElevenRoasView.as_view()),
    path('eleven-product-roas/', ElevenProductRoasView.as_view()),
    path('eleven-keyword-roas/', ElevenKeywordRoasView.as_view()),
    path('crawler/eleven-product-daily/run/', St11ProductDailyCrawlView.as_view()),
    path('eleven-loss-products/delete/', ElevenLossDeleteView.as_view()),
    path('eleven-loss-products/mark-deleted/', ElevenLossMarkDeletedView.as_view()),
    path('crawler/stats/', CrawlerAccountStatsView.as_view()),
    path('crawler/accounts/excel-upload/', CrawlerAccountExcelUploadView.as_view()),
    path('crawler/accounts/excel-sample/', CrawlerAccountExcelSampleView.as_view()),
    path('gmarket-summary/', GmarketSummaryView.as_view()),
    path('profit-dashboard/', ProfitDashboardView.as_view()),
    path('eleven-summary/', ElevenSummaryView.as_view()),
    path('overview/', OverviewView.as_view()),
    path('telegram/send/', TelegramSendView.as_view()),
    path('cpc2/control/', Cpc2ControlView.as_view()),
    path('cron/apply/', CronApplyView.as_view()),
    path('ai/control/', AiControlView.as_view()),
    path('gmarket-control/stop/', GmarketControlStopView.as_view()),
    path('gmarket-control/status/', GmarketControlStatusView.as_view()),
    path('eleven-ad-strategy/accounts/', St11AdStrategyAccountsView.as_view()),
    path('eleven-ad-strategy/campaigns/', St11AdStrategyCampaignsView.as_view()),
    path('eleven-ad-strategy/control/', St11AdStrategyControlView.as_view()),
    path('eleven-ad-strategy/schedule/', St11AdStrategyScheduleView.as_view()),
    path('eleven-ad-strategy/runs/', St11AdStrategyRunsView.as_view()),
    path('eleven-ad-strategy/logs/', St11AdStrategyLogView.as_view()),
    path('sms/receive/', SmsReceiveView.as_view()),
    path('sms/otp-test/', SmsOtpTestView.as_view()),
    path('crawler/unblock/', AccountUnblockView.as_view()),
    path('sms/phones/', SmsPhoneSettingView.as_view()),
    path('sms/latest/', SmsLatestView.as_view()),
    path('ad-detail/', AdDetailView.as_view()),
    # smsApp 게이트웨이
    path('mms/receive/', MmsReceiveView.as_view()),
    path('sms/outbox/', SmsOutboxView.as_view()),
    path('sms/outbox/history/', SmsOutboxHistoryView.as_view()),
    path('sms/outbox/<int:pk>/result/', SmsOutboxResultView.as_view()),
    path('sms/devices/', SmsDeviceListView.as_view()),
    path('sms/devices/heartbeat/', SmsHeartbeatView.as_view()),
    path('sms/devices/change-number/', SmsChangeNumberView.as_view()),
    path('eleven-my/sync/', ElevenMyProductSyncView.as_view()),
    path('gmarket-my/products/', GmarketMyProductListView.as_view()),
    path('gmarket-my/accounts/', GmarketMyAccountsView.as_view()),
    path('gmarket/dashboard/', GmarketDashboardView.as_view()),
    path('gmarket/crawl-status/', GmarketCrawlStatusView.as_view()),
    path('gmarket/recrawl/', GmarketRecrawlView.as_view()),
    path('gmarket/cost-detail/', GmarketCostDetailView.as_view()),
    path('gmarket/ad-daily/', GmarketAdDailyView.as_view()),
    path('gmarket/adgroup/', GmarketAdGroupView.as_view()),
    path('gmarket/product-roas/', GmarketProductRoasView.as_view()),
    path('gmarket/roas-accounts/', GmarketRoasAccountsView.as_view()),
    path('gmarket/loss-products/', GmarketLossProductsView.as_view()),
    path('gmarket/loss-products/mark-deleted/', GmarketLossMarkDeletedView.as_view()),
    path('gmarket/loss-products/delete/', GmarketLossDeleteView.as_view()),
    path('gmarket/keyword-crawl/', GmarketKeywordCrawlView.as_view()),
    path('gmarket/keyword-upload/', GmarketKeywordUploadView.as_view()),
    path('gmarket/keyword-status/', GmarketKeywordStatusView.as_view()),
    path('gmarket/keyword-cumulative/', GmarketKeywordCumulativeView.as_view()),
    path('gmarket/focus-targets/', GmarketFocusTargetsView.as_view()),
    path('eleven-my/products/', ElevenMyProductListView.as_view()),
    path('eleven-my/products/<int:pk>/', ElevenMyProductDetailView.as_view()),
    path('eleven-my/accounts/', ElevenMyProductAccountSummaryView.as_view()),
    path('eleven-my/duplicates/', ElevenMyProductDuplicateView.as_view()),
    path('eleven-my/integrated-sync/', ElevenIntegratedSyncView.as_view()),
    path('eleven-my/sync-status/', ElevenSyncStatusView.as_view()),
    path('eleven-my/block-clear/', ElevenBlockClearView.as_view()),
    path('crawler/blocked/', BlockedAccountsView.as_view()),
    path('timeseries/', GmarketTimeseriesView.as_view()),
    path('tax/vat/', TaxVatSummaryView.as_view()),
    path('eleven-grades-latest/', ElevenGradeLatestView.as_view()),
    path('eleven/auth-status/', ElevenAuthStatusView.as_view()),
    path('eleven/verify-otp/', ElevenVerifyOtpView.as_view()),
    path('seller-login/<str:seller_id>/', SellerAutoLoginView.as_view()),
]
