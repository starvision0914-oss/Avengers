from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmailAccountViewSet, EmailMessageViewSet, EmailLabelViewSet, EmailSyncView, EmailSendView

router = DefaultRouter()
router.register(r'accounts', EmailAccountViewSet)
router.register(r'messages', EmailMessageViewSet, basename='message')
router.register(r'labels', EmailLabelViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('sync/', EmailSyncView.as_view()),
    path('send/', EmailSendView.as_view()),
]
