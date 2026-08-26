from django.urls import path

from apps.lotteon.views import (
    LotteonDashboardView, LotteonAccountsView, LotteonMyProductListView, LotteonSuspendAllNoMatchView,
    LotteonSuspendSelectedView, LotteonPrecheckDiffView,
)

urlpatterns = [
    path('dashboard/', LotteonDashboardView.as_view()),
    path('accounts/', LotteonAccountsView.as_view()),
    path('my/products/', LotteonMyProductListView.as_view()),
    path('my/products/suspend-no-match/', LotteonSuspendAllNoMatchView.as_view()),
    path('my/products/suspend-selected/', LotteonSuspendSelectedView.as_view()),
    path('my/products/precheck-diff/', LotteonPrecheckDiffView.as_view()),
]
