"""Ventes dans l'administration : les tarifs se saisissent ici, le reste se consulte."""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from stocks.admin import ReadOnlyAdminMixin

from .models import CustomerOrder, CustomerOrderLine, EdiMessage, SalePrice


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
