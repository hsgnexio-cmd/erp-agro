from decimal import Decimal

from rest_framework import serializers

from previsions.forecast import week_label
from qualite.services import compute_allergens
from referentiel.choices import ArticleType
from referentiel.models import Article, Location, ProductionLine, Site
from stocks.models import Lot

from . import orders
from .models import (
    LineStop,
    MasterPlan,
    ProductionDeclaration,
    ProductionOrder,
    StopCategory,
)


class ProductionOrderSerializer(serializers.ModelSerializer):
    article_code = serializers.CharField(source="article.code", read_only=True)
    article_name = serializers.CharField(source="article.name", read_only=True)
    article_type = serializers.CharField(source="article.article_type", read_only=True)
    unit = serializers.CharField(source="article.unit", read_only=True)
    site_code = serializers.CharField(source="site.code", read_only=True)
    line_code = serializers.CharField(source="line.code", read_only=True, default=None)
    output_location_code = serializers.CharField(source="output_location.code", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    produced_quantity = serializers.SerializerMethodField()
    mass_yield = serializers.SerializerMethodField()

    class Meta:
        model = ProductionOrder
        fields = [
            "id",
            "number",
            "article",
            "article_code",
            "article_name",
            "article_type",
            "unit",
            "planned_quantity",
            "planned_date",
            "sequence",
            "site",
            "site_code",
            "line",
            "line_code",
            "output_location_code",
            "status",
            "status_label",
            "comment",
            "produced_quantity",
            "mass_yield",
        ]

    def get_produced_quantity(self, order) -> str:
        return str(orders.produced_quantity(order))

    def get_mass_yield(self, order) -> str | None:
        if order.status != "termine":
            return None
        value = orders.yield_report(order)["mass_yield"]
        return None if value is None else str(value)


class DeclarationSerializer(serializers.ModelSerializer):
    lot_number = serializers.CharField(source="lot.number", read_only=True)
    quantity = serializers.DecimalField(
        source="lot.initial_quantity", max_digits=14, decimal_places=3, read_only=True
    )
    user_name = serializers.CharField(source="user.username", read_only=True, default=None)

    class Meta:
        model = ProductionDeclaration
        fields = [
            "id",
            "lot",
            "lot_number",
            "quantity",
            "declared_at",
            "user_name",
            "comment",
            "fefo_deviations",
            "run_start",
            "run_end",
            "scrap_quantity",
            "scrap_reason",
        ]


class ProductionOrderDetailSerializer(ProductionOrderSerializer):
    needs = serializers.SerializerMethodField()
    declarations = DeclarationSerializer(many=True, read_only=True)
    yield_report = serializers.SerializerMethodField()
    allergens = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )

    class Meta(ProductionOrderSerializer.Meta):
        fields = [
            *ProductionOrderSerializer.Meta.fields,
            "needs",
            "declarations",
            "yield_report",
            "allergens",
            "created_by_name",
            "launched_at",
            "closed_at",
        ]

    def get_needs(self, order) -> list[dict]:
        return [
            {
                "component": need.component.id,
                "component_code": need.component.code,
                "component_name": need.component.name,
                "unit": need.unit,
                "net": str(need.net),
                "gross": str(need.gross),
            }
            for need in orders.theoretical_needs(order.article, order.planned_quantity)
        ]

    def get_yield_report(self, order) -> dict:
        report = orders.yield_report(order)
        return {
            "produced": str(report["produced"]),
            "mass_yield": None if report["mass_yield"] is None else str(report["mass_yield"]),
            "below_target": report["below_target"],
            "target": str(orders.YIELD_TARGET),
            "components": [
                {
                    "component_code": row["component"].code,
                    "unit": row["unit"],
                    "theoretical": str(row["theoretical"]),
                    "actual": str(row["actual"]),
                    "gap_pct": None if row["gap_pct"] is None else str(row["gap_pct"]),
                }
                for row in report["components"]
            ],
        }

    def get_allergens(self, order) -> list[str]:
        return [row["allergen"].name for row in compute_allergens(order.article)]


class OrderInputSerializer(serializers.Serializer):
    article = serializers.PrimaryKeyRelatedField(queryset=Article.objects.all())
    planned_quantity = serializers.DecimalField(max_digits=14, decimal_places=3)
    planned_date = serializers.DateField()
    line = serializers.PrimaryKeyRelatedField(
        queryset=ProductionLine.objects.all(), required=False, allow_null=True, default=None
    )
    site = serializers.PrimaryKeyRelatedField(
        queryset=Site.objects.all(), required=False, allow_null=True, default=None
    )
    sequence = serializers.IntegerField(min_value=1, default=1)
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class OrderUpdateSerializer(serializers.Serializer):
    planned_quantity = serializers.DecimalField(max_digits=14, decimal_places=3, required=False)
    planned_date = serializers.DateField(required=False)
    line = serializers.PrimaryKeyRelatedField(
        queryset=ProductionLine.objects.all(), required=False, allow_null=True
    )
    sequence = serializers.IntegerField(min_value=1, required=False)
    comment = serializers.CharField(required=False, allow_blank=True)


class ConsumptionInputSerializer(serializers.Serializer):
    lot = serializers.PrimaryKeyRelatedField(queryset=Lot.objects.all())
    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0"))
    justification = serializers.CharField(required=False, allow_blank=True, default="")


class DeclarationInputSerializer(serializers.Serializer):
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0.001"))
    production_date = serializers.DateField(required=False)
    comment = serializers.CharField(required=False, allow_blank=True, default="")
    consumptions = ConsumptionInputSerializer(many=True)
    run_start = serializers.DateTimeField(required=False, allow_null=True, default=None)
    run_end = serializers.DateTimeField(required=False, allow_null=True, default=None)
    scrap_quantity = serializers.DecimalField(
        max_digits=14, decimal_places=3, required=False, default=Decimal("0")
    )
    scrap_reason = serializers.CharField(required=False, allow_blank=True, default="")


# --- Plan de production (phase 9b) -----------------------------------------------------


class MasterPlanSerializer(serializers.ModelSerializer):
    week_label = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    forecast_version_number = serializers.CharField(
        source="forecast_version.number", read_only=True, default=None
    )
    frozen_by_name = serializers.SerializerMethodField()

    class Meta:
        model = MasterPlan
        fields = [
            "id", "week", "week_label", "status", "status_label", "forecast_version_number",
            "computed_at", "frozen_at", "frozen_by_name",
        ]  # fmt: skip

    def get_week_label(self, obj) -> str:
        return week_label(obj.week)

    def get_frozen_by_name(self, obj) -> str:
        return obj.frozen_by.username if obj.frozen_by else ""


class PlanComputeInputSerializer(serializers.Serializer):
    week = serializers.DateField()


def _finished_products():
    return Article.objects.filter(article_type=ArticleType.FINISHED_PRODUCT)


class PlanQuantityInputSerializer(serializers.Serializer):
    article = serializers.PrimaryKeyRelatedField(queryset=_finished_products())
    day = serializers.DateField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3)


class PlanLineInputSerializer(serializers.Serializer):
    article = serializers.PrimaryKeyRelatedField(queryset=_finished_products())
    line = serializers.PrimaryKeyRelatedField(queryset=ProductionLine.objects.all())


class PlanAddArticleInputSerializer(serializers.Serializer):
    article = serializers.PrimaryKeyRelatedField(queryset=_finished_products())
    line = serializers.PrimaryKeyRelatedField(
        queryset=ProductionLine.objects.all(), required=False, allow_null=True
    )


# --- Arrêts de ligne et TRS (phase 10) -------------------------------------------------


class LineStopSerializer(serializers.ModelSerializer):
    line_code = serializers.CharField(source="line.code", read_only=True)
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    production_order_number = serializers.CharField(
        source="production_order.number", read_only=True, default=None
    )
    minutes = serializers.IntegerField(read_only=True)
    planned = serializers.BooleanField(source="is_planned", read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.username", read_only=True, default=""
    )
    cancelled_by_name = serializers.CharField(
        source="cancelled_by.username", read_only=True, default=""
    )

    class Meta:
        model = LineStop
        fields = [
            "id", "line", "line_code", "started_at", "ended_at", "minutes", "category",
            "category_label", "planned", "production_order", "production_order_number",
            "comment", "created_at", "created_by_name", "cancelled_at", "cancelled_by_name",
            "cancel_reason",
        ]  # fmt: skip


class LineStopInputSerializer(serializers.Serializer):
    line = serializers.PrimaryKeyRelatedField(queryset=ProductionLine.objects.all())
    started_at = serializers.DateTimeField()
    ended_at = serializers.DateTimeField()
    category = serializers.ChoiceField(choices=StopCategory.choices)
    production_order = serializers.PrimaryKeyRelatedField(
        queryset=ProductionOrder.objects.all(), required=False, allow_null=True
    )
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class StopCancelInputSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=True)
