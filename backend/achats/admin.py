"""Achats dans l'administration.

Les tarifs se saisissent ici (rôles acheteur et admin). Les commandes et réceptions
se consultent seulement : elles se créent dans l'application, qui applique les règles
(numérotation, statuts, contrôles, création des lots).
"""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from stocks.admin import ReadOnlyAdminMixin

from .models import PurchaseOrder, PurchaseOrderLine, Reception, ReceptionLine, SupplierPrice


@admin.register(SupplierPrice)
class SupplierPriceAdmin(SimpleHistoryAdmin):
    list_display = ("supplier_article", "unit_price", "valid_from", "valid_to")
    list_filter = ("supplier_article__supplier",)
    search_fields = ("supplier_article__article__code", "supplier_article__supplier__name")
    list_select_related = ("supplier_article__supplier", "supplier_article__article")


class PurchaseOrderLineInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = PurchaseOrderLine
    extra = 0
    fields = ("article", "quantity", "unit", "unit_price")
    readonly_fields = fields


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(ReadOnlyAdminMixin, SimpleHistoryAdmin):
    list_display = ("number", "supplier", "order_date", "expected_delivery_date", "status")
    list_filter = ("status", "supplier")
    search_fields = ("number", "supplier__name")
    inlines = [PurchaseOrderLineInline]


class ReceptionLineInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = ReceptionLine
    extra = 0
    fields = (
        "order_line",
        "quantity",
        "supplier_lot_number",
        "expiry_date",
        "temperature",
        "is_compliant",
        "non_compliance_reasons",
        "lot",
    )
    readonly_fields = fields


@admin.register(Reception)
class ReceptionAdmin(ReadOnlyAdminMixin, SimpleHistoryAdmin):
    list_display = ("number", "order", "received_at", "received_by", "delivery_note_number")
    search_fields = ("number", "order__number", "delivery_note_number")
    inlines = [ReceptionLineInline]
