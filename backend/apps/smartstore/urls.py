from django.urls import path
from . import views

urlpatterns = [
    path('accounts/', views.AccountListView.as_view()),
    path('accounts/<int:pk>/', views.AccountDetailView.as_view()),
    path('dashboard/', views.DashboardView.as_view()),
    path('products/', views.ProductListView.as_view()),
    path('products/sync/', views.ProductSyncView.as_view()),
    path('products/excel/', views.ProductExcelView.as_view()),
    path('products/suspend-preview/', views.SuspendPreviewView.as_view()),
    path('products/suspend/', views.SuspendProductsView.as_view()),
    path('product-stats/', views.ProductStatsView.as_view()),
    path('crawl-status/', views.CrawlStatusView.as_view()),
    path('naver-product-roas/', views.NaverProductRoasView.as_view()),
    path('clean-violations/', views.CleanViolationListView.as_view()),
    path('clean-violations/<int:account_id>/', views.CleanViolationDetailView.as_view()),
]
