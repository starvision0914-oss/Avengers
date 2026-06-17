from django.contrib import admin
from .models import LottoHistory


@admin.register(LottoHistory)
class LottoHistoryAdmin(admin.ModelAdmin):
    list_display = ('drw_no', 'drw_date', 'num1', 'num2', 'num3', 'num4', 'num5', 'num6', 'bonus')
    search_fields = ('drw_no',)
    ordering = ('-drw_no',)
