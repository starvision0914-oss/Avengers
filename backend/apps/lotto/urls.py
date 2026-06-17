from django.urls import path
from .views import (
    StatsView, HistoryView, SyncView, ImportCsvView, PredictView,
    PredictBruteView, PredictMirrorPrevView, ExportCsvView,
    PredictionListView, PredictionCheckView, PredictionDeleteView,
)

urlpatterns = [
    path('stats/', StatsView.as_view()),
    path('history/', HistoryView.as_view()),
    path('sync/', SyncView.as_view()),
    path('import-csv/', ImportCsvView.as_view()),
    path('export-csv/', ExportCsvView.as_view()),
    path('predict/', PredictView.as_view()),
    path('predict-brute/', PredictBruteView.as_view()),
    path('predict-mirror-prev/', PredictMirrorPrevView.as_view()),
    path('predictions/', PredictionListView.as_view()),
    path('predictions/<int:pk>/check/', PredictionCheckView.as_view()),
    path('predictions/<int:pk>/', PredictionDeleteView.as_view()),
]
