from decimal import Decimal

from rest_framework import serializers

from referentiel.models import Article, Customer, CustomerWarehouse, Location
from stocks.models import Lot, StockMovement

from .models import CustomerOrder, CustomerOrderLine, EdiMessage, SalePrice


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
        ]

    def get_to_be_priced(self, line) -> bool:
        return line.unit_price is None


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

    class Meta(CustomerOrderSerializer.Meta):
        fields = [
            *CustomerOrderSerializer.Meta.fields,
            "lines",
            "edi_message_id",
            "created_by_name",
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


# --- Expéditions (minimales, phase 5 ; la préparation viendra en 7b) -------------------


class ShipmentSerializer(serializers.ModelSerializer):
    lot_number = serializers.CharField(source="lot.number", read_only=True)
    article_code = serializers.CharField(source="lot.article.code", read_only=True)
    unit = serializers.CharField(source="lot.article.unit", read_only=True)
    customer_code = serializers.CharField(source="customer_warehouse.customer.code", read_only=True)
    warehouse_code = serializers.CharField(source="customer_warehouse.code", read_only=True)
    warehouse_name = serializers.CharField(source="customer_warehouse.name", read_only=True)
    quantity = serializers.SerializerMethodField()

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "reference",
            "created_at",
            "lot",
            "lot_number",
            "article_code",
            "unit",
            "quantity",
            "customer_code",
            "warehouse_code",
            "warehouse_name",
        ]

    def get_quantity(self, movement: StockMovement) -> str:
        return str(-movement.quantity)  # une expédition est une sortie : on l'affiche en positif


class ShipmentInputSerializer(serializers.Serializer):
    lot = serializers.PrimaryKeyRelatedField(queryset=Lot.objects.all())
    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0.001"))
    warehouse = serializers.PrimaryKeyRelatedField(queryset=CustomerWarehouse.objects.all())
