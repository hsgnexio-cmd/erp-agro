"""Lots et mouvements : consultation seule dans l'administration.

Ils sont créés uniquement par les opérations de l'ERP (réception…), jamais à la main.
"""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    Alert,
    Inventory,
    InventoryLine,
    Lot,
    LotStatusChange,
    StockMovement,
    TemperatureReading,
)


class ReadOnlyAdminMixin:
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class StockMovementInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = StockMovement
    fk_name = "lot"  # le lot du mouvement (et non le lot fabriqué d'une consommation)
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


@admin.register(TemperatureReading)
class TemperatureReadingAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("measured_at", "location", "temperature", "is_compliant", "user")
    list_filter = ("is_compliant", "location__site", "location")


class InventoryLineInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = InventoryLine
    extra = 0
    fields = ("location", "lot", "expected_quantity", "counted_quantity", "added_during_count")
    readonly_fields = fields


@admin.register(Inventory)
class InventoryAdmin(ReadOnlyAdminMixin, SimpleHistoryAdmin):
    list_display = ("number", "site", "location", "status", "opened_at", "closed_at")
    list_filter = ("status", "site")
    inlines = [InventoryLineInline]


@admin.register(Alert)
class AlertAdmin(ReadOnlyAdminMixin, SimpleHistoryAdmin):
    list_display = ("created_at", "alert_type", "level", "message", "resolved_at")
    list_filter = ("alert_type", "level", ("resolved_at", admin.EmptyFieldListFilter))
