from django.contrib import admin

from .models import Player, Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "cash", "last_daily_claim", "created_at")


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("name", "nickname", "position", "grade", "team", "overall", "potential", "age")
    list_filter = ("position", "grade", "team")
    search_fields = ("name", "nickname")
