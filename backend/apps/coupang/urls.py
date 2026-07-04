from django.urls import path

from apps.coupang.views import CoupangDashboardView

urlpatterns = [
    path('dashboard/', CoupangDashboardView.as_view()),
]
