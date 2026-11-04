"""Conversion des données du référentiel en JSON pour l'API (et inversement)."""

from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from . import services
from .models import (
    Allergen,
    Article,
    BillOfMaterials,
    BOMLine,
    Customer,
    CustomerWarehouse,
    Location,
    MaterialCategory,
    ProductFamily,
    ProductionLine,
    Recipe,
    Site,
    Supplier,
    SupplierArticle,
)
from .permissions import can_edit_allergens


class SiteSerializer(serializers.ModelSerializer):
    site_type_label = serializers.CharField(source="get_site_type_display", read_only=True)

    class Meta:
        model = Site
        fields = ["id", "code", "name", "site_type", "site_type_label", "city", "active"]


class LocationSerializer(serializers.ModelSerializer):
    site_code = serializers.CharField(source="site.code", read_only=True)
    temperature_class_label = serializers.CharField(
        source="get_temperature_class_display", read_only=True
    )

    class Meta:
        model = Location
        fields = [
            "id",
            "site",
            "site_code",
            "code",
            "name",
            "temperature_class",
            "temperature_class_label",
            "min_temperature",
            "max_temperature",
            "active",
        ]


class ProductFamilySerializer(serializers.ModelSerializer):
    site_code = serializers.CharField(source="site.code", read_only=True)

    class Meta:
        model = ProductFamily
        fields = ["id", "code", "name", "site", "site_code"]


class MaterialCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialCategory
        fields = [
            "id",
            "code",
            "name",
            "temperature_class",
            "date_type",
            "min_remaining_shelf_life_pct",
        ]


class AllergenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Allergen
        fields = ["id", "code", "name", "order"]


class CustomerSerializer(serializers.ModelSerializer):
    customer_type_label = serializers.CharField(source="get_customer_type_display", read_only=True)
    warehouse_count = serializers.IntegerField(source="warehouses.count", read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id",
            "code",
            "name",
            "customer_type",
            "customer_type_label",
            "sells_brand",
            "sells_private_label",
            "min_remaining_shelf_life_pct",
            "warehouse_count",
            "active",
        ]


class CustomerWarehouseSerializer(serializers.ModelSerializer):
    customer_code = serializers.CharField(source="customer.code", read_only=True)

    class Meta:
        model = CustomerWarehouse
        fields = [
            "id",
            "customer",
            "customer_code",
            "code",
            "name",
            "address",
            "postal_code",
            "city",
            "active",
        ]


class RecipeSerializer(serializers.ModelSerializer):
    family_code = serializers.CharField(source="family.code", read_only=True)

    class Meta:
        model = Recipe
        fields = ["id", "code", "name", "family", "family_code", "active"]


class ArticleSerializer(serializers.ModelSerializer):
    article_type_label = serializers.CharField(source="get_article_type_display", read_only=True)
    category_code = serializers.CharField(source="category.code", read_only=True, default=None)
    recipe_code = serializers.CharField(source="recipe.code", read_only=True, default=None)
    brand_code = serializers.CharField(read_only=True)
    allergen_names = serializers.SlugRelatedField(
        source="allergens", many=True, read_only=True, slug_field="name"
    )
    has_bom = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            "id",
            "code",
            "name",
            "article_type",
            "article_type_label",
            "unit",
            "category",
            "category_code",
            "recipe",
            "recipe_code",
            "brand_customer",
            "brand_code",
            "format_size",
            "shelf_life_days",
            "date_type",
            "storage_temperature_class",
            "technical_sheet",
            "specifications",
            "allergens",
            "allergen_names",
            "has_bom",
            "active",
        ]
        read_only_fields = ["date_type", "storage_temperature_class"]
        extra_kwargs = {"code": {"required": False}}

    def get_has_bom(self, article: Article) -> bool:
        return hasattr(article, "bom")

    def validate(self, attrs):
        allergens = attrs.get("allergens")
        if allergens is not None:
            current = set(self.instance.allergens.all()) if self.instance else set()
            if set(allergens) != current and not can_edit_allergens(self.context["request"].user):
                raise PermissionDenied("Seuls les rôles qualité et admin modifient les allergènes.")
            article = Article(
                article_type=attrs.get("article_type", getattr(self.instance, "article_type", ""))
            )
            services.validate_allergens(article, allergens)
        return attrs


class BOMLineSerializer(serializers.ModelSerializer):
    component_code = serializers.CharField(source="component.code", read_only=True)
    component_name = serializers.CharField(source="component.name", read_only=True)
    component_type = serializers.CharField(source="component.article_type", read_only=True)
    gross_quantity = serializers.DecimalField(max_digits=14, decimal_places=4, read_only=True)

    class Meta:
        model = BOMLine
        fields = [
            "id",
            "bom",
            "component",
            "component_code",
            "component_name",
            "component_type",
            "quantity",
            "unit",
            "loss_rate",
            "gross_quantity",
        ]


class BillOfMaterialsSerializer(serializers.ModelSerializer):
    article_code = serializers.CharField(source="article.code", read_only=True)
    article_name = serializers.CharField(source="article.name", read_only=True)
    article_unit = serializers.CharField(source="article.unit", read_only=True)
    lines = BOMLineSerializer(many=True, read_only=True)

    class Meta:
        model = BillOfMaterials
        fields = [
            "id",
            "article",
            "article_code",
            "article_name",
            "article_unit",
            "base_quantity",
            "comment",
            "lines",
        ]


class SupplierSerializer(serializers.ModelSerializer):
    category_codes = serializers.SlugRelatedField(
        source="categories", many=True, read_only=True, slug_field="code"
    )

    class Meta:
        model = Supplier
        fields = [
            "id",
            "code",
            "name",
            "address",
            "postal_code",
            "city",
            "country",
            "email",
            "phone",
            "lead_time_days",
            "categories",
            "category_codes",
            "audited",
            "last_audit_date",
            "active",
        ]


class SupplierArticleSerializer(serializers.ModelSerializer):
    supplier_code = serializers.CharField(source="supplier.code", read_only=True)
    article_code = serializers.CharField(source="article.code", read_only=True)
    article_name = serializers.CharField(source="article.name", read_only=True)

    class Meta:
        model = SupplierArticle
        fields = [
            "id",
            "supplier",
            "supplier_code",
            "article",
            "article_code",
            "article_name",
            "supplier_reference",
            "is_main_supplier",
            "min_order_quantity",
        ]


class ProductionLineSerializer(serializers.ModelSerializer):
    site_code = serializers.CharField(source="site.code", read_only=True)
    family_codes = serializers.SlugRelatedField(
        source="families", many=True, read_only=True, slug_field="code"
    )

    class Meta:
        model = ProductionLine
        fields = [
            "id",
            "code",
            "name",
            "site",
            "site_code",
            "families",
            "family_codes",
            "formats",
            "capacity_per_hour",
            "active",
        ]
