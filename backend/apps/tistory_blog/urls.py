from django.urls import path
from . import views

urlpatterns = [
    path('posts/generate/', views.GeneratePostView.as_view()),
    path('accounts/', views.AccountListView.as_view()),
    path('accounts/<int:pk>/', views.AccountDetailView.as_view()),
    path('posts/', views.PostListView.as_view()),
    path('posts/<int:pk>/', views.PostDetailView.as_view()),
    path('posts/<int:pk>/publish/', views.PostPublishView.as_view()),
]
