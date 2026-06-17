from django.urls import path

from . import views

urlpatterns = [
    path('products/', views.KeywordProductListView.as_view()),
    path('products/<int:pk>/', views.KeywordProductDetailView.as_view()),
    path('products/upload/', views.KeywordProductUploadView.as_view()),
    path('products/csv-upload/', views.KeywordProductCsvUploadView.as_view()),
    path('products/soldout-txt/', views.KeywordSoldoutTxtUploadView.as_view()),
    path('products/sync/', views.KeywordProductSyncView.as_view()),
    path('products/stats/', views.KeywordProductStatsView.as_view()),
    path('products/changed-fields/', views.KeywordProductChangedFieldsView.as_view()),
    path('products/excel/', views.KeywordProductExcelExportView.as_view()),
    path('products/wcodes/', views.KeywordProductWCodesView.as_view()),
    path('products/delete-all/', views.KeywordProductDeleteAllView.as_view()),
    path('products/delete-ids/', views.KeywordProductDeleteByIdsView.as_view()),
    path('products/dedupe/', views.KeywordProductDedupeView.as_view()),
    path('products/distinct/', views.KeywordDistinctValuesView.as_view()),
]
