from decimal import Decimal

from rest_framework import serializers

from referentiel.models import Location

from . import services
from .models import Lot, LotStatusChange, StockMovement


class LotSerializer(serializers.ModelSerializer):
    article_code = serializers.CharField(source="article.code", read_only=True)
    article_name = serializers.CharField(source="article.name", read_only=True)
    article_type = serializers.CharField(source="article.article_type", read_only=True)
    article_temperature_class = serializers.CharField(
        source="article.storage_temperature_class", read_only=True
    )
    unit = serializers.CharField(source="article.unit", read_only=True)
    supplier_code = serializers.CharField(source="supplier.code", read_only=True, default=None)
    location_code = serializers.CharField(source="location.code", read_only=True)
    site_code = serializers.CharField(source="location.site.code", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    quantity = serializers.DecimalField(
        source="current_quantity", max_digits=14, decimal_places=3, read_only=True
    )
    reception_number = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = Lot
        fields = [
            "id",
            "number",
            "article",
            "article_code",
            "article_name",
            "article_type",
            "article_temperature_class",
            "unit",
            "supplier",
            "supplier_code",
            "supplier_lot_number",
            "reception_date",
            "date_type",
            "expiry_date",
            "is_expired",
            "initial_quantity",
            "quantity",
            "location",
            "location_code",
            "site_code",
            "status",
            "status_label",
            "block_reason",
            "reception_number",
            "created_at",
        ]

    def get_reception_number(self, lot: Lot) -> str | None:
        line = getattr(lot, "reception_line", None)
        return line.reception.number if line else None

    def get_is_expired(self, lot: Lot) -> bool:
        return services.is_expired(lot)


class LotStatusChangeSerializer(serializers.ModelSerializer):
    from_status_label = serializers.CharField(source="get_from_status_display", read_only=True)
    to_status_label = serializers.CharField(source="get_to_status_display", read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True, default=None)

    class Meta:
        model = LotStatusChange
        fields = [
            "id",
            "from_status",
            "from_status_label",
            "to_status",
            "to_status_label",
            "reason",
            "user_name",
            "changed_at",
        ]


class LotDetailSerializer(LotSerializer):
    """Fiche lot : en plus, le stock par emplacement et le journal des statuts."""

    stock_by_location = serializers.SerializerMethodField()
    status_changes = LotStatusChangeSerializer(many=True, read_only=True)

    class Meta(LotSerializer.Meta):
        fields = [*LotSerializer.Meta.fields, "stock_by_location", "status_changes"]

    def get_stock_by_location(self, lot: Lot) -> list[dict]:
        return [
            {
                "location": location.id,
                "location_code": location.code,
                "location_name": location.name,
                "site_code": location.site.code,
                "quantity": str(quantity),
            }
            for location, quantity in services.stock_by_location(lot)
        ]


class StockMovementSerializer(serializers.ModelSerializer):
    lot_number = serializers.CharField(source="lot.number", read_only=True)
    article_code = serializers.CharField(source="lot.article.code", read_only=True)
    unit = serializers.CharField(source="lot.article.unit", read_only=True)
    movement_type_label = serializers.CharField(source="get_movement_type_display", read_only=True)
    location_code = serializers.CharField(source="location.code", read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True, default=None)

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "lot",
            "lot_number",
            "article_code",
            "movement_type",
            "movement_type_label",
            "quantity",
            "unit",
            "location",
            "location_code",
            "created_at",
            "user_name",
            "reason",
            "reference",
            "corrected_movement",
        ]


# --- Saisies des actions ------------------------------------------------------


class StatusChangeInputSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class TransferInputSerializer(serializers.Serializer):
    from_location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    to_location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0.001"))
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class CorrectionInputSerializer(serializers.Serializer):
    reason = serializers.CharField()
    quantity = serializers.DecimalField(
        max_digits=14, decimal_places=3, required=False, allow_null=True, default=None
    )
