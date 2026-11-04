"""Lots et mouvements : consultation seule dans l'administration.

Ils sont créés uniquement par les opérations de l'ERP (réception…), jamais à la main.
"""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Lot, LotStatusChange, StockMovement


class ReadOnlyAdminMixin:
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class StockMovementInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = StockMovement
    extra = 0
    fields = ("created_at", "movement_type", "quantity", "location", "user", "reason", "reference")
    readonly_fields = fields


class LotStatusChangeInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = LotStatusChange
    extra = 0
    fields = ("changed_at", "from_status", "to_status", "reason", "user")
    readonly_fields = fields


@admin.register(Lot)
class LotAdmin(ReadOnlyAdminMixin, SimpleHistoryAdmin):
    list_display = (
        "number",
        "article",
        "supplier_lot_number",
        "expiry_date",
        "initial_quantity",
        "location",
        "status",
    )
    list_filter = ("status", "location__site", "article__article_type")
    search_fields = ("number", "supplier_lot_number", "article__code", "article__name")
    inlines = [LotStatusChangeInline, StockMovementInline]


@admin.register(StockMovement)
class StockMovementAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = (
        "created_at",
        "lot",
        "movement_type",
        "quantity",
        "location",
        "user",
        "reference",
    )
    list_filter = ("movement_type", "location__site")
    search_fields = ("lot__number", "reference")
