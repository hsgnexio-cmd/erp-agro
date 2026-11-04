from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from referentiel.models import Article, Customer, CustomerWarehouse, Location
from stocks.models import Lot

from . import shipping
from .models import (
    CustomerOrder,
    CustomerOrderLine,
    EdiMessage,
    OrderStatus,
    Pallet,
    PalletLine,
    SalePrice,
    Shipment,
    ShipmentLine,
    ShipmentStatus,
)

ZERO = Decimal("0")


class SalePriceSerializer(serializers.ModelSerializer):
    customer_code = serializers.CharField(source="customer.code", read_only=True)
    article_code = serializers.CharField(source="article.code", read_only=True)
    article_name = serializers.CharField(source="article.name", read_only=True)

    class Meta:
        model = SalePrice
        fields = [
            "id",
            "customer",
            "customer_code",
            "article",
            "article_code",
            "article_name",
            "unit_price",
            "valid_from",
            "valid_to",
        ]


class OrderLineSerializer(serializers.ModelSerializer):
    article_code = serializers.CharField(source="article.code", read_only=True)
    article_name = serializers.CharField(source="article.name", read_only=True)
    amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True, allow_null=True
    )
    to_be_priced = serializers.SerializerMethodField()
    shipped_quantity = serializers.SerializerMethodField()

    class Meta:
        model = CustomerOrderLine
        fields = [
            "id",
            "article",
            "article_code",
            "article_name",
            "quantity",
            "unit_price",
            "amount",
            "to_be_priced",
            "shipped_quantity",
        ]

    def get_to_be_priced(self, line) -> bool:
        return line.unit_price is None

    def get_shipped_quantity(self, line) -> str | None:
        """Quantité livrée (vide tant que la commande n'est pas expédiée)."""
        if line.order.status != OrderStatus.SHIPPED:
            return None
        shipped = [
            item.quantity
            for item in line.shipment_lines.all()
            if item.shipment.status == ShipmentStatus.SHIPPED
        ]
        return str(sum(shipped, ZERO))


class CustomerOrderSerializer(serializers.ModelSerializer):
    customer_code = serializers.CharField(source="customer.code", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    source_label = serializers.CharField(source="get_source_display", read_only=True)
    total_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    line_count = serializers.IntegerField(source="lines.count", read_only=True)
    to_be_priced = serializers.SerializerMethodField()

    class Meta:
        model = CustomerOrder
        fields = [
            "id",
            "number",
            "customer",
            "customer_code",
            "customer_name",
            "warehouse",
            "warehouse_code",
            "warehouse_name",
            "customer_reference",
            "received_at",
            "requested_delivery_date",
            "status",
            "status_label",
            "source",
            "source_label",
            "total_amount",
            "line_count",
            "to_be_priced",
            "comment",
        ]

    def get_to_be_priced(self, order) -> bool:
        return any(line.unit_price is None for line in order.lines.all())


class CustomerOrderDetailSerializer(CustomerOrderSerializer):
    lines = OrderLineSerializer(many=True, read_only=True)
    edi_message_id = serializers.CharField(
        source="edi_message.message_id", read_only=True, default=None
    )
    created_by_name = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )
    shipments = serializers.SerializerMethodField()

    class Meta(CustomerOrderSerializer.Meta):
        fields = [
            *CustomerOrderSerializer.Meta.fields,
            "lines",
            "edi_message_id",
            "created_by_name",
            "shipments",
        ]

    def get_shipments(self, order) -> list[dict]:
        return [
            {
                "id": shipment.id,
                "number": shipment.number,
                "status": shipment.status,
                "status_label": shipment.get_status_display(),
            }
            for shipment in order.shipments.all()
        ]


class OrderLineInputSerializer(serializers.Serializer):
    article = serializers.PrimaryKeyRelatedField(queryset=Article.objects.all())
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)


class CustomerOrderInputSerializer(serializers.Serializer):
    """Saisie manuelle d'une commande (reçue par téléphone, par exemple)."""

    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    warehouse = serializers.PrimaryKeyRelatedField(queryset=CustomerWarehouse.objects.all())
    requested_delivery_date = serializers.DateField()
    customer_reference = serializers.CharField(required=False, allow_blank=True, default="")
    comment = serializers.CharField(required=False, allow_blank=True, default="")
    lines = OrderLineInputSerializer(many=True)


class EdiMessageSerializer(serializers.ModelSerializer):
    customer_code = serializers.CharField(source="customer.code", read_only=True, default=None)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    order = serializers.SerializerMethodField()

    class Meta:
        model = EdiMessage
        fields = [
            "id",
            "message_id",
            "customer_code",
            "received_at",
            "status",
            "status_label",
            "errors",
            "payload",
            "order",
        ]

    def get_order(self, message) -> dict | None:
        order = getattr(message, "order", None)
        return {"id": order.id, "number": order.number} if order else None


# --- Préparation et expédition (partie 7b) ---------------------------------------------


class ShipmentLineSerializer(serializers.ModelSerializer):
    article_code = serializers.CharField(source="lot.article.code", read_only=True)
    article_name = serializers.CharField(source="lot.article.name", read_only=True)
    unit = serializers.CharField(source="lot.article.unit", read_only=True)
    lot_number = serializers.CharField(source="lot.number", read_only=True)
    expiry_date = serializers.DateField(source="lot.expiry_date", read_only=True)
    location_code = serializers.CharField(source="location.code", read_only=True)

    class Meta:
        model = ShipmentLine
        fields = [
            "id",
            "order_line",
            "article_code",
            "article_name",
            "unit",
            "lot",
            "lot_number",
            "expiry_date",
            "location",
            "location_code",
            "quantity",
            "fefo_justification",
            "movement",
        ]


class PalletLineSerializer(serializers.ModelSerializer):
    article_code = serializers.CharField(source="shipment_line.lot.article.code", read_only=True)
    article_name = serializers.CharField(source="shipment_line.lot.article.name", read_only=True)
    lot_number = serializers.CharField(source="shipment_line.lot.number", read_only=True)
    expiry_date = serializers.DateField(source="shipment_line.lot.expiry_date", read_only=True)

    class Meta:
        model = PalletLine
        fields = ["id", "article_code", "article_name", "lot_number", "expiry_date", "quantity"]


class PalletSerializer(serializers.ModelSerializer):
    lines = PalletLineSerializer(many=True, read_only=True)
    total_quantity = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)

    class Meta:
        model = Pallet
        fields = ["id", "sscc", "rank", "total_quantity", "lines"]


class ShipmentSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.number", read_only=True)
    customer_code = serializers.CharField(source="order.customer.code", read_only=True)
    customer_name = serializers.CharField(source="order.customer.name", read_only=True)
    warehouse_code = serializers.CharField(source="order.warehouse.code", read_only=True)
    warehouse_name = serializers.CharField(source="order.warehouse.name", read_only=True)
    requested_delivery_date = serializers.DateField(
        source="order.requested_delivery_date", read_only=True
    )
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    prepared_by_name = serializers.CharField(
        source="prepared_by.username", read_only=True, default=None
    )
    shipped_by_name = serializers.CharField(
        source="shipped_by.username", read_only=True, default=None
    )
    total_quantity = serializers.SerializerMethodField()
    pallet_count = serializers.SerializerMethodField()
    on_time = serializers.SerializerMethodField()

    class Meta:
        model = Shipment
        fields = [
            "id",
            "number",
            "order",
            "order_number",
            "customer_code",
            "customer_name",
            "warehouse_code",
            "warehouse_name",
            "requested_delivery_date",
            "status",
            "status_label",
            "prepared_at",
            "prepared_by_name",
            "carrier",
            "loading_temperature",
            "shipped_at",
            "shipped_by_name",
            "refusal_reason",
            "total_quantity",
            "pallet_count",
            "on_time",
        ]

    def get_total_quantity(self, shipment) -> str:
        return str(sum((line.quantity for line in shipment.lines.all()), Decimal("0")))

    def get_pallet_count(self, shipment) -> int:
        return len(shipment.pallets.all())

    def get_on_time(self, shipment) -> bool | None:
        """Expédié au plus tard la veille de la livraison demandée (transport J+1) ?"""
        if shipment.status != ShipmentStatus.SHIPPED or shipment.shipped_at is None:
            return None
        return timezone.localdate(shipment.shipped_at) <= shipping.on_time_limit(shipment.order)


class ShipmentDetailSerializer(ShipmentSerializer):
    lines = ShipmentLineSerializer(many=True, read_only=True)
    pallets = PalletSerializer(many=True, read_only=True)
    summary = serializers.SerializerMethodField()

    class Meta(ShipmentSerializer.Meta):
        fields = [*ShipmentSerializer.Meta.fields, "lines", "pallets", "summary"]

    def get_summary(self, shipment) -> list[dict]:
        """Commandé, préparé et rupture, ligne de commande par ligne de commande."""
        prepared: dict[int, Decimal] = {}
        for line in shipment.lines.all():
            prepared[line.order_line_id] = prepared.get(line.order_line_id, ZERO) + line.quantity
        rows = []
        for line in shipment.order.lines.all():
            done = prepared.get(line.pk, ZERO)
            rows.append(
                {
                    "order_line": line.pk,
                    "article_code": line.article.code,
                    "article_name": line.article.name,
                    "ordered": str(line.quantity),
                    "prepared": str(done),
                    "missing": str(max(line.quantity - done, ZERO)),
                }
            )
        return rows


class PrepareLineInputSerializer(serializers.Serializer):
    order_line = serializers.PrimaryKeyRelatedField(queryset=CustomerOrderLine.objects.all())
    lot = serializers.PrimaryKeyRelatedField(queryset=Lot.objects.all())
    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0"))
    justification = serializers.CharField(required=False, allow_blank=True, default="")


class PrepareInputSerializer(serializers.Serializer):
    lines = PrepareLineInputSerializer(many=True)


class ShipInputSerializer(serializers.Serializer):
    carrier = serializers.CharField(max_length=100)
    temperature = serializers.DecimalField(max_digits=4, decimal_places=1)


class CancelPreparationInputSerializer(serializers.Serializer):
    reason = serializers.CharField()
