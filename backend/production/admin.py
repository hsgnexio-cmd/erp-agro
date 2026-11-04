"""Ordres de fabrication : consultation seule, ils se gèrent dans l'application."""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from stocks.admin import ReadOnlyAdminMixin

from .models import ProductionDeclaration, ProductionOrder


class DeclarationInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = ProductionDeclaration
    extra = 0
    fields = ("declared_at", "lot", "user", "comment", "fefo_deviations")
    readonly_fields = fields


@admin.register(ProductionOrder)
class ProductionOrderAdmin(ReadOnlyAdminMixin, SimpleHistoryAdmin):
    list_display = ("number", "article", "planned_quantity", "planned_date", "line", "status")
    list_filter = ("status", "site", "line")
    search_fields = ("number", "article__code")
    inlines = [DeclarationInline]
