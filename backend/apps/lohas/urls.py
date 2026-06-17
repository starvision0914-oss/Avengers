from django.urls import path

from .views import (
    BulkEditListCategoriesView,
    BulkEditRunView,
    JobDetailView,
    JobListView,
    JobStopView,
    RestockStartView,
)

urlpatterns = [
    path('restock/', RestockStartView.as_view()),
    path('bulk-edit/list-categories/', BulkEditListCategoriesView.as_view()),
    path('bulk-edit/run/', BulkEditRunView.as_view()),
    path('jobs/', JobListView.as_view()),
    path('jobs/<str:job_id>/', JobDetailView.as_view()),
    path('jobs/<str:job_id>/stop/', JobStopView.as_view()),
]
