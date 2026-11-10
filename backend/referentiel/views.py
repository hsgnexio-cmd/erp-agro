"""Adresses de l'API du référentiel : /api/referentiel/…"""

from datetime import date

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import calendar, serializers, services
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
    SiteClosure,
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


class ProductionLineViewSet(ReferentielViewSet):
    """Lignes de production. ?article=12 ne garde que les lignes qui acceptent cet article."""

    queryset = ProductionLine.objects.select_related("site").prefetch_related("families")
    serializer_class = serializers.ProductionLineSerializer
    filterset_fields = ["site", "site__code", "active"]

    def get_queryset(self):
        queryset = super().get_queryset()
        article_id = self.request.query_params.get("article")
        if article_id:
            article = Article.objects.filter(pk=article_id).first()
            if article is None or article.article_type != "PF":
                return queryset.none()
            ids = [line.pk for line in queryset if services.line_accepts(line, article) is None]
            queryset = queryset.filter(pk__in=ids)
        return queryset


# --- Calendrier (phase 11) ---------------------------------------------------------------


class CalendarView(APIView):
    """Jours fériés et fermetures exceptionnelles d'une année : /api/referentiel/calendar/"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        value = request.query_params.get("year") or str(timezone.localdate().year)
        if not value.isdigit() or not 2000 <= int(value) <= 2100:
            raise ValidationError({"year": ["Année invalide."]})
        year = int(value)
        closures = SiteClosure.objects.filter(
            start_date__lte=date(year, 12, 31), end_date__gte=date(year, 1, 1)
        ).select_related("site")
        return Response(
            {
                "year": year,
                "rules": [
                    {"activity": "Production (usines NAN, REN)", "days": "du lundi au vendredi"},
                    {
                        "activity": "Expédition (PFN), livraisons des enseignes, prise de commande",
                        "days": "du lundi au samedi",
                    },
                    {
                        "activity": "Réception des fournisseurs (MPE), délais fournisseurs",
                        "days": "du lundi au vendredi",
                    },
                ],
                "holidays": [
                    {
                        "date": day,
                        "label": label,
                        "weekday": calendar.WEEKDAY_NAMES[day.weekday()],
                    }
                    for day, label in calendar.french_holidays(year).items()
                ],
                "closures": [
                    {
                        "id": closure.id,
                        "site_code": closure.site.code,
                        "site_name": closure.site.name,
                        "start_date": closure.start_date,
                        "end_date": closure.end_date,
                        "reason": closure.reason,
                    }
                    for closure in closures
                ],
            }
        )
