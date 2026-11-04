"""Ventes dans l'administration : les tarifs se saisissent ici, le reste se consulte."""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from stocks.admin import ReadOnlyAdminMixin

from .models import (
    CustomerOrder,
    CustomerOrderLine,
    EdiMessage,
    Pallet,
    PalletLine,
    SalePrice,
    Shipment,
    ShipmentLine,
)


@admin.register(SalePrice)
class SalePriceAdmin(SimpleHistoryAdmin):
    list_display = ("customer", "article", "unit_price", "valid_from", "valid_to")
    list_filter = ("customer",)
    search_fields = ("article__code", "article__name")


class CustomerOrderLineInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = CustomerOrderLine
    extra = 0
    fields = ("article", "quantity", "unit_price")
    readonly_fields = fields


@admin.register(CustomerOrder)
class CustomerOrderAdmin(ReadOnlyAdminMixin, SimpleHistoryAdmin):
    list_display = (
        "number",
        "customer",
        "warehouse",
        "requested_delivery_date",
        "status",
        "source",
    )
    list_filter = ("status", "source", "customer")
    search_fields = ("number", "customer_reference")
    inlines = [CustomerOrderLineInline]


@admin.register(EdiMessage)
class EdiMessageAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("message_id", "customer", "received_at", "status")
    list_filter = ("status", "customer")
    search_fields = ("message_id",)


class ShipmentLineInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = ShipmentLine
    extra = 0
    fields = ("order_line", "lot", "location", "quantity", "fefo_justification", "movement")
    readonly_fields = fields


@admin.register(Shipment)
class ShipmentAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("number", "order", "status", "prepared_at", "shipped_at", "carrier")
    list_filter = ("status",)
    search_fields = ("number", "order__number", "pallets__sscc")
    inlines = [ShipmentLineInline]


class PalletLineInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = PalletLine
    extra = 0
    fields = ("shipment_line", "quantity")
    readonly_fields = fields


@admin.register(Pallet)
class PalletAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("sscc", "shipment", "rank")
    search_fields = ("sscc", "shipment__number")
    inlines = [PalletLineInline]
