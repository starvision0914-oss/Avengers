from django.contrib import admin
from .models import SpeedgoItem, CategoryMapping, SpeedgoLog


@admin.register(SpeedgoItem)
class SpeedgoItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'domemea_no', 'original_name', 'wholesale_price',
                    'naver_category_path', 'status', 'collected_at')
    search_fields = ('domemea_no', 'original_name')
    list_filter = ('status',)


@admin.register(CategoryMapping)
class CategoryMappingAdmin(admin.ModelAdmin):
    list_display = ('id', 'naver_path', 'market', 'market_category_id')
    search_fields = ('naver_path', 'market_category_id')
    list_filter = ('market',)


@admin.register(SpeedgoLog)
class SpeedgoLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'stage', 'level', 'message', 'created_at')
    list_filter = ('stage', 'level')
