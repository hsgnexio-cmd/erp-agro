"""Adresses de l'API du référentiel : /api/referentiel/…"""

from rest_framework import viewsets

from . import serializers
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
    Recipe,
    Site,
    Supplier,
    SupplierArticle,
)
from .permissions import ReferentielPermission


class ReferentielViewSet(viewsets.ModelViewSet):
    """Lecture, création et modification. Pas de suppression : on désactive."""

    permission_classes = [ReferentielPermission]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]


class SiteViewSet(ReferentielViewSet):
    queryset = Site.objects.all()
    serializer_class = serializers.SiteSerializer
    filterset_fields = ["site_type", "active"]
    search_fields = ["code", "name", "city"]


class LocationViewSet(ReferentielViewSet):
    queryset = Location.objects.select_related("site")
    serializer_class = serializers.LocationSerializer
    filterset_fields = ["site", "site__code", "temperature_class", "active"]
    search_fields = ["code", "name"]


class ProductFamilyViewSet(ReferentielViewSet):
    queryset = ProductFamily.objects.select_related("site")
    serializer_class = serializers.ProductFamilySerializer
    search_fields = ["code", "name"]


class MaterialCategoryViewSet(ReferentielViewSet):
    queryset = MaterialCategory.objects.all()
    serializer_class = serializers.MaterialCategorySerializer
    search_fields = ["code", "name"]


class AllergenViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Allergen.objects.all()
    serializer_class = serializers.AllergenSerializer
    permission_classes = [ReferentielPermission]
    pagination_class = None


class CustomerViewSet(ReferentielViewSet):
    queryset = Customer.objects.prefetch_related("warehouses")
    serializer_class = serializers.CustomerSerializer
    filterset_fields = ["customer_type", "sells_brand", "sells_private_label", "active"]
    search_fields = ["code", "name"]


class CustomerWarehouseViewSet(ReferentielViewSet):
    queryset = CustomerWarehouse.objects.select_related("customer")
    serializer_class = serializers.CustomerWarehouseSerializer
    filterset_fields = ["customer", "customer__code", "active"]
    search_fields = ["code", "name", "city"]


class RecipeViewSet(ReferentielViewSet):
    queryset = Recipe.objects.select_related("family")
    serializer_class = serializers.RecipeSerializer
    filterset_fields = ["family", "family__code", "active"]
    search_fields = ["code", "name"]


class ArticleViewSet(ReferentielViewSet):
    queryset = Article.objects.select_related(
        "category", "recipe", "brand_customer", "bom"
    ).prefetch_related("allergens")
    serializer_class = serializers.ArticleSerializer
    filterset_fields = [
        "article_type",
        "category",
        "category__code",
        "recipe",
        "recipe__code",
        "brand_customer",
        "date_type",
        "active",
    ]
    search_fields = ["code", "name"]
    ordering_fields = ["code", "name", "shelf_life_days"]


class BillOfMaterialsViewSet(ReferentielViewSet):
    queryset = BillOfMaterials.objects.select_related("article").prefetch_related(
        "lines__component"
    )
    serializer_class = serializers.BillOfMaterialsSerializer
    filterset_fields = ["article", "article__code", "article__article_type"]
    search_fields = ["article__code", "article__name"]


class BOMLineViewSet(ReferentielViewSet):
    queryset = BOMLine.objects.select_related("bom__article", "component")
    serializer_class = serializers.BOMLineSerializer
    filterset_fields = ["bom", "component", "component__code"]


class SupplierViewSet(ReferentielViewSet):
    queryset = Supplier.objects.prefetch_related("categories")
    serializer_class = serializers.SupplierSerializer
    filterset_fields = ["categories", "audited", "active"]
    search_fields = ["code", "name", "city"]


class SupplierArticleViewSet(ReferentielViewSet):
    queryset = SupplierArticle.objects.select_related("supplier", "article")
    serializer_class = serializers.SupplierArticleSerializer
    filterset_fields = ["supplier", "article", "is_main_supplier"]
    search_fields = ["article__code", "article__name", "supplier_reference"]
