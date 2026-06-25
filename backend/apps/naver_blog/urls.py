from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.DashboardView.as_view()),
    path('settings/', views.SettingView.as_view()),
    path('accounts/', views.AccountListView.as_view()),
    path('accounts/<int:pk>/', views.AccountDetailView.as_view()),
    path('keywords/', views.KeywordListView.as_view()),
    path('keywords/collect/', views.KeywordCollectView.as_view()),
    path('keywords/<int:pk>/', views.KeywordDetailView.as_view()),
    path('posts/', views.PostListView.as_view()),
    path('posts/manual/', views.PostManualCreateView.as_view()),
    path('posts/generate/', views.GeneratePostView.as_view()),
    path('posts/<int:pk>/', views.PostDetailView.as_view()),
    path('posts/<int:pk>/publish/', views.PostPublishView.as_view()),
]
