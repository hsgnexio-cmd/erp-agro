"""Prévisions dans l'administration : consultation seule (saisie dans l'application)."""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from stocks.admin import ReadOnlyAdminMixin

from .models import ForecastAdjustment, ForecastLine, ForecastVersion, Promotion


@admin.register(Promotion)
class PromotionAdmin(ReadOnlyAdminMixin, SimpleHistoryAdmin):
    list_display = (
        "customer", "article", "first_week", "last_week", "coefficient", "announced_on",
        "cancelled_at",
    )  # fmt: skip
    list_filter = ("customer",)
    search_fields = ("article__code", "article__name")


@admin.register(ForecastAdjustment)
class ForecastAdjustmentAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("customer", "article", "week", "quantity", "reason", "created_at", "created_by")
    list_filter = ("customer", "week")
    search_fields = ("article__code", "reason")


class ForecastLineInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = ForecastLine
    extra = 0
    fields = ("week", "customer", "article", "base_quantity", "promo_coefficient", "quantity")
    readonly_fields = fields


@admin.register(ForecastVersion)
class ForecastVersionAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("number", "created_at", "source", "first_week", "created_by")
    list_filter = ("source",)
    search_fields = ("number",)
    inlines = [ForecastLineInline]
