from decimal import Decimal

from rest_framework import serializers

from referentiel.models import Article, Location, Site, Supplier

from . import services
from .models import PurchaseOrder, PurchaseOrderLine, Reception, ReceptionLine, SupplierPrice


class SupplierPriceSerializer(serializers.ModelSerializer):
    supplier_code = serializers.CharField(source="supplier_article.supplier.code", read_only=True)
    article_code = serializers.CharField(source="supplier_article.article.code", read_only=True)
    unit = serializers.CharField(source="supplier_article.article.unit", read_only=True)

    class Meta:
        model = SupplierPrice
        fields = [
            "id",
            "supplier_article",
            "supplier_code",
            "article_code",
            "unit",
            "unit_price",
            "valid_from",
            "valid_to",
        ]


# --- Commandes --------------------------------------------------------------


class PurchaseOrderLineSerializer(serializers.ModelSerializer):
    article_code = serializers.CharField(source="article.code", read_only=True)
    article_name = serializers.CharField(source="article.name", read_only=True)
    # Indiquent à l'écran de réception les saisies obligatoires (DLC/DDM, température)
    article_date_type = serializers.CharField(source="article.date_type", read_only=True)
    article_temperature_class = serializers.CharField(
        source="article.storage_temperature_class", read_only=True
    )
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    received_quantity = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)

    class Meta:
        model = PurchaseOrderLine
        fields = [
            "id",
            "article",
            "article_code",
            "article_name",
            "article_date_type",
            "article_temperature_class",
            "quantity",
            "unit",
            "unit_price",
            "amount",
            "received_quantity",
        ]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier_code = serializers.CharField(source="supplier.code", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    delivery_site_code = serializers.CharField(source="delivery_site.code", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )
    total_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    lines = PurchaseOrderLineSerializer(many=True, read_only=True)
    reception_ids = serializers.PrimaryKeyRelatedField(
        source="receptions", many=True, read_only=True
    )

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "number",
            "supplier",
            "supplier_code",
            "supplier_name",
            "delivery_site",
            "delivery_site_code",
            "order_date",
            "expected_delivery_date",
            "status",
            "status_label",
            "comment",
            "created_by_name",
            "created_at",
            "sent_at",
            "total_amount",
            "lines",
            "reception_ids",
        ]


class OrderLineInputSerializer(serializers.Serializer):
    article = serializers.PrimaryKeyRelatedField(queryset=Article.objects.all())
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    unit_price = serializers.DecimalField(
        max_digits=12, decimal_places=4, required=False, allow_null=True
    )


class PurchaseOrderInputSerializer(serializers.Serializer):
    """Données saisies pour créer ou modifier une commande en brouillon."""

    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all())
    delivery_site = serializers.PrimaryKeyRelatedField(queryset=Site.objects.all())
    order_date = serializers.DateField(required=False)
    expected_delivery_date = serializers.DateField(required=False, allow_null=True)
    comment = serializers.CharField(required=False, allow_blank=True)
    lines = OrderLineInputSerializer(many=True)

    def create(self, validated_data):
        return services.create_purchase_order(user=self.context["request"].user, **validated_data)

    def update(self, instance, validated_data):
        return services.update_purchase_order(instance, **validated_data)


# --- Réceptions -------------------------------------------------------------


class ReceptionLineSerializer(serializers.ModelSerializer):
    article_code = serializers.CharField(source="order_line.article.code", read_only=True)
    article_name = serializers.CharField(source="order_line.article.name", read_only=True)
    unit = serializers.CharField(source="order_line.unit", read_only=True)
    lot_number = serializers.CharField(source="lot.number", read_only=True, default=None)
    lot_status = serializers.CharField(source="lot.status", read_only=True, default=None)

    class Meta:
        model = ReceptionLine
        fields = [
            "id",
            "order_line",
            "article_code",
            "article_name",
            "unit",
            "quantity",
            "supplier_lot_number",
            "expiry_date",
            "temperature",
            "appearance_ok",
            "comment",
            "is_compliant",
            "non_compliance_reasons",
            "lot",
            "lot_number",
            "lot_status",
        ]


class ReceptionSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.number", read_only=True)
    supplier_name = serializers.CharField(source="order.supplier.name", read_only=True)
    received_by_name = serializers.CharField(
        source="received_by.username", read_only=True, default=None
    )
    location_code = serializers.CharField(source="location.code", read_only=True)
    lines = ReceptionLineSerializer(many=True, read_only=True)
    is_compliant = serializers.SerializerMethodField()

    class Meta:
        model = Reception
        fields = [
            "id",
            "number",
            "order",
            "order_number",
            "supplier_name",
            "received_at",
            "received_by_name",
            "delivery_note_number",
            "documents_ok",
            "location",
            "location_code",
            "comment",
            "is_compliant",
            "lines",
        ]

    def get_is_compliant(self, reception: Reception) -> bool:
        return all(line.is_compliant for line in reception.lines.all())


class ReceptionLineInputSerializer(serializers.Serializer):
    order_line = serializers.PrimaryKeyRelatedField(queryset=PurchaseOrderLine.objects.all())
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"))
    supplier_lot_number = serializers.CharField(required=False, allow_blank=True, default="")
    expiry_date = serializers.DateField(required=False, allow_null=True, default=None)
    temperature = serializers.DecimalField(
        max_digits=4, decimal_places=1, required=False, allow_null=True, default=None
    )
    appearance_ok = serializers.BooleanField(default=True)
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class ReceptionInputSerializer(serializers.Serializer):
    order = serializers.PrimaryKeyRelatedField(queryset=PurchaseOrder.objects.all())
    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    delivery_note_number = serializers.CharField()
    documents_ok = serializers.BooleanField(default=True)
    received_at = serializers.DateTimeField(required=False)
    comment = serializers.CharField(required=False, allow_blank=True, default="")
    lines = ReceptionLineInputSerializer(many=True)

    def create(self, validated_data):
        return services.create_reception(user=self.context["request"].user, **validated_data)
