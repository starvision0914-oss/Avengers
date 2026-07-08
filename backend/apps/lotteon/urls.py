from django.urls import path

from apps.lotteon.views import LotteonDashboardView, LotteonAccountsView

urlpatterns = [
    path('dashboard/', LotteonDashboardView.as_view()),
    path('accounts/', LotteonAccountsView.as_view()),
]
