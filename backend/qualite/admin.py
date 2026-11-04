from django.contrib import admin

from stocks.admin import ReadOnlyAdminMixin

from .models import ProductRecall


@admin.register(ProductRecall)
class ProductRecallAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    """Rappels : consultation seule, ils se lancent depuis l'application."""

    list_display = ("number", "origin_lot", "created_at", "created_by")
    search_fields = ("number", "origin_lot__number")
    filter_horizontal = ("blocked_lots",)
