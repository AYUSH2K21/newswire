from django.contrib import admin
from .models import SavedArticle, NewsCache, SearchLog


@admin.register(SavedArticle)
class SavedArticleAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "created_at")
    search_fields = ("title", "user__username")
    list_filter = ("created_at",)


@admin.register(NewsCache)
class NewsCacheAdmin(admin.ModelAdmin):
    list_display = ("query", "cached_at")
    search_fields = ("query",)


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ("user", "keyword", "searched_at")
    search_fields = ("keyword", "user__username")
    list_filter = ("searched_at",)