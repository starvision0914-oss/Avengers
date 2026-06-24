from django.urls import path
from . import views

urlpatterns = [
    path('accounts/', views.AccountListView.as_view()),
    path('accounts/<int:pk>/', views.AccountDetailView.as_view()),
    path('dashboard/', views.DashboardView.as_view()),
    path('crawl-status/', views.CrawlStatusView.as_view()),
]
