from django.urls import path
from .views import (
    StatsView, ItemListView, MatchCategoriesView,
    CollectMyboxView, ItemDeleteView, AddManualItemView,
    SpeedgoRunView, SpeedgoRunStatusView, SpeedgoSessionCloseView,
)

urlpatterns = [
    path('stats/', StatsView.as_view()),
    path('items/', ItemListView.as_view()),
    path('items/<int:pk>/', ItemDeleteView.as_view()),
    path('items/add-manual/', AddManualItemView.as_view()),
    path('match-categories/', MatchCategoriesView.as_view()),
    path('collect-mybox/', CollectMyboxView.as_view()),
    path('run/', SpeedgoRunView.as_view()),
    path('run/status/', SpeedgoRunStatusView.as_view()),
    path('session/close/', SpeedgoSessionCloseView.as_view()),
]
