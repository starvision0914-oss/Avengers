from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("daily/", views.claim_daily, name="claim_daily"),
    path("roster/", views.roster, name="roster"),
    path("roster/bulk-release/", views.bulk_release_players, name="bulk_release_players"),
    path("player/<int:pk>/", views.player_detail, name="player_detail"),
    path("player/<int:pk>/train/", views.train_player, name="train_player"),
    path("player/<int:pk>/release/", views.release_player, name="release_player"),
    path("player/<int:pk>/breakthrough/", views.breakthrough_player, name="breakthrough_player"),
    path("player/<int:pk>/trade/", views.trade_player, name="trade_player"),
    path("scout/", views.scout, name="scout"),
    path("match/", views.match, name="match"),
    path("lineup/", views.lineup, name="lineup"),
    path("records/", views.records, name="records"),
]
