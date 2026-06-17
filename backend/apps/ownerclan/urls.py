from django.urls import path

from . import views

urlpatterns = [
    path('products/', views.OwnerClanProductListView.as_view()),
    path('products/<int:pk>/', views.OwnerClanProductDetailView.as_view()),
    path('products/upload/', views.OwnerClanProductUploadView.as_view()),
    path('products/csv-upload/', views.OwnerClanProductCsvUploadView.as_view()),
    path('products/soldout-txt/', views.OwnerClanSoldoutTxtUploadView.as_view()),
    path('products/sync/', views.OwnerClanProductSyncView.as_view()),
    path('products/stats/', views.OwnerClanProductStatsView.as_view()),
    path('products/changed-fields/', views.OwnerClanProductChangedFieldsView.as_view()),
    path('products/excel/', views.OwnerClanProductExcelExportView.as_view()),
    path('products/wcodes/', views.OwnerClanProductWCodesView.as_view()),
    path('products/delete-all/', views.OwnerClanProductDeleteAllView.as_view()),
    path('products/delete-ids/', views.OwnerClanProductDeleteByIdsView.as_view()),
    path('products/dedupe/', views.OwnerClanProductDedupeView.as_view()),
    path('products/apply-eleven-name/', views.OwnerClanApplyElevenNameView.as_view()),
    path('products/distinct/', views.OwnerClanDistinctValuesView.as_view()),

    path('my/copy/', views.MyProductCopyView.as_view()),
    path('my/products/upload/', views.MyProductUploadView.as_view()),
    path('my/products/', views.MyProductListView.as_view()),
    path('my/products/<int:pk>/', views.MyProductDetailView.as_view()),
    path('my/products/delete-all/', views.MyProductDeleteAllView.as_view()),
    path('my/products/delete-ids/', views.MyProductDeleteByIdsView.as_view()),
    path('my/products/dedupe/', views.MyProductDedupeView.as_view()),
    path('my/products/distinct/', views.MyProductDistinctValuesView.as_view()),
    path('my/products/wcodes/', views.MyProductWCodesView.as_view()),
    path('my/products/excel/', views.MyProductExcelExportView.as_view()),
]
