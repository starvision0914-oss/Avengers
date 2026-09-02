from django.urls import path

from apps.toss.views import TossAccountsView, TossDashboardView, TossCampaignListView, TossAccountSummaryView

urlpatterns = [
    path('accounts/', TossAccountsView.as_view()),
    path('dashboard/', TossDashboardView.as_view()),
    path('campaigns/', TossCampaignListView.as_view()),
    path('account-summary/', TossAccountSummaryView.as_view()),
]
