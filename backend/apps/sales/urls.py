from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (SalesRecordViewSet, SalesUploadView, SalesSummaryView, SalesUploadLogViewSet,
                    SalesUnmatchedView, SalesMatchView)

router = DefaultRouter()
router.register(r'records', SalesRecordViewSet)
router.register(r'upload-logs', SalesUploadLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('upload/', SalesUploadView.as_view()),
    path('summary/', SalesSummaryView.as_view()),
    path('unmatched/', SalesUnmatchedView.as_view()),
    path('match/', SalesMatchView.as_view()),
]
