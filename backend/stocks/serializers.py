from rest_framework import serializers

from .models import Lot, StockMovement


class LotSerializer(serializers.ModelSerializer):
    article_code = serializers.CharField(source="article.code", read_only=True)
    article_name = serializers.CharField(source="article.name", read_only=True)
    article_type = serializers.CharField(source="article.article_type", read_only=True)
    unit = serializers.CharField(source="article.unit", read_only=True)
    supplier_code = serializers.CharField(source="supplier.code", read_only=True, default=None)
    location_code = serializers.CharField(source="location.code", read_only=True)
    site_code = serializers.CharField(source="location.site.code", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    quantity = serializers.DecimalField(
        source="current_quantity", max_digits=14, decimal_places=3, read_only=True
    )
    reception_number = serializers.SerializerMethodField()

    class Meta:
        model = Lot
        fields = [
            "id",
            "number",
            "article",
            "article_code",
            "article_name",
            "article_type",
            "unit",
            "supplier",
            "supplier_code",
            "supplier_lot_number",
            "reception_date",
            "date_type",
            "expiry_date",
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
        ]
