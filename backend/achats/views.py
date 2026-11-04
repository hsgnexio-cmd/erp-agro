"""API des achats : /api/achats/…"""

from django.db.models import Prefetch
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from comptes.permissions import WriteRolesPermission
from comptes.roles import Role
from referentiel.models import SupplierArticle

from . import services
from .models import PurchaseOrder, PurchaseOrderLine, Reception, SupplierPrice
from .serializers import (
    PurchaseOrderInputSerializer,
    PurchaseOrderSerializer,
    ReceptionInputSerializer,
    ReceptionSerializer,
    SupplierPriceSerializer,
)

PURCHASING = [Role.ADMIN, Role.ACHETEUR]
WAREHOUSE = [Role.ADMIN, Role.MAGASINIER]


class SupplierPriceViewSet(viewsets.ModelViewSet):
    queryset = SupplierPrice.objects.select_related(
        "supplier_article__supplier", "supplier_article__article"
    )
    serializer_class = SupplierPriceSerializer
    permission_classes = [WriteRolesPermission]
    write_roles = PURCHASING
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    filterset_fields = [
        "supplier_article",
        "supplier_article__supplier",
        "supplier_article__article",
    ]


class SupplierCatalogView(APIView):
    """Articles qu'un fournisseur peut livrer, avec le prix en vigueur et le minimum de commande.

    Utilisé par le formulaire de commande : /api/achats/catalog/?supplier=3&date=2026-11-04
    """

    permission_classes = [WriteRolesPermission]

    def get(self, request: Request) -> Response:
        supplier_id = request.query_params.get("supplier")
        if not supplier_id:
            raise ValidationError({"supplier": "Indique le fournisseur."})
        on_date = parse_date(request.query_params.get("date", "")) or timezone.localdate()
        links = (
            SupplierArticle.objects.filter(supplier_id=supplier_id, article__active=True)
            .select_related("article")
            .prefetch_related("prices")
            .order_by("article__code")
        )
        items = []
        for link in links:
            price = services.current_price(link, on_date)
            items.append(
                {
                    "article": link.article.id,
                    "article_code": link.article.code,
                    "article_name": link.article.name,
                    "unit": link.article.unit,
                    # Décimales envoyées en texte, comme dans le reste de l'API
                    "min_order_quantity": (
                        str(link.min_order_quantity) if link.min_order_quantity else None
                    ),
                    "unit_price": str(price.unit_price) if price else None,
                }
            )
        return Response(items)


class PurchaseOrderViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    queryset = PurchaseOrder.objects.select_related(
        "supplier", "delivery_site", "created_by"
    ).prefetch_related(
        Prefetch("lines", queryset=PurchaseOrderLine.objects.select_related("article")),
        "lines__reception_lines",
        "receptions",
    )
    permission_classes = [WriteRolesPermission]
    write_roles = PURCHASING
    filterset_fields = ["status", "supplier", "delivery_site"]
    search_fields = ["number", "supplier__name", "supplier__code"]
    ordering_fields = ["order_date", "expected_delivery_date", "number"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return PurchaseOrderInputSerializer
        return PurchaseOrderSerializer

    def _read(self, order, status_code=status.HTTP_200_OK) -> Response:
        order = self.get_queryset().get(pk=order.pk)
        return Response(PurchaseOrderSerializer(order).data, status=status_code)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._read(serializer.save(), status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            self.get_object(), data=request.data, partial=kwargs.get("partial", False)
        )
        serializer.is_valid(raise_exception=True)
        return self._read(serializer.save())

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        """Passe la commande de « brouillon » à « envoyée »."""
        return self._read(services.send_order(self.get_object()))

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._read(services.cancel_order(self.get_object()))


class ReceptionViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Reception.objects.select_related(
        "order__supplier", "received_by", "location"
    ).prefetch_related("lines__order_line__article", "lines__lot")
    permission_classes = [WriteRolesPermission]
    write_roles = WAREHOUSE
    filterset_fields = ["order", "order__supplier"]
    search_fields = ["number", "delivery_note_number", "order__number"]

    def get_serializer_class(self):
        if self.action == "create":
            return ReceptionInputSerializer
        return ReceptionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reception = self.get_queryset().get(pk=serializer.save().pk)
        return Response(ReceptionSerializer(reception).data, status=status.HTTP_201_CREATED)
