"""API des ventes : /api/ventes/… (tarifs, commandes clients, EDI, expéditions)."""

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
from referentiel.models import Customer
from stocks.choices import MovementType
from stocks.models import StockMovement

from . import edi, orders, services
from .models import CustomerOrder, EdiMessage, SalePrice
from .serializers import (
    CustomerOrderDetailSerializer,
    CustomerOrderInputSerializer,
    CustomerOrderSerializer,
    EdiMessageSerializer,
    SalePriceSerializer,
    ShipmentInputSerializer,
    ShipmentSerializer,
)

SALES = [Role.ADMIN, Role.COMMERCIAL]
WAREHOUSE = [Role.ADMIN, Role.MAGASINIER]


class SalePriceViewSet(viewsets.ModelViewSet):
    queryset = SalePrice.objects.select_related("customer", "article")
    serializer_class = SalePriceSerializer
    permission_classes = [WriteRolesPermission]
    write_roles = SALES
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    filterset_fields = ["customer", "customer__code", "article"]
    search_fields = ["article__code", "article__name"]


class CustomerOrderViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    queryset = CustomerOrder.objects.select_related(
        "customer", "warehouse", "edi_message", "created_by"
    ).prefetch_related("lines__article")
    permission_classes = [WriteRolesPermission]
    write_roles = SALES
    filterset_fields = ["status", "customer", "customer__code", "source", "requested_delivery_date"]
    search_fields = ["number", "customer_reference", "customer__name"]
    ordering_fields = ["received_at", "requested_delivery_date"]

    def get_serializer_class(self):
        if self.action == "create":
            return CustomerOrderInputSerializer
        if self.action == "list":
            return CustomerOrderSerializer
        return CustomerOrderDetailSerializer

    def _detail(self, order, status_code=status.HTTP_200_OK) -> Response:
        order = self.get_queryset().get(pk=order.pk)
        return Response(CustomerOrderDetailSerializer(order).data, status=status_code)

    def create(self, request, *args, **kwargs):
        data = CustomerOrderInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        order = orders.create_order(user=request.user, source="manuel", **data.validated_data)
        return self._detail(order, status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._detail(orders.cancel_order(self.get_object()))


class OrderableArticlesView(APIView):
    """Produits commandables par une enseigne, prix en vigueur et date de livraison au plus tôt."""

    permission_classes = [WriteRolesPermission]

    def get(self, request: Request) -> Response:
        customer = Customer.objects.filter(pk=request.query_params.get("customer") or 0).first()
        if customer is None:
            raise ValidationError({"customer": ["Enseigne introuvable."]})
        earliest = orders.earliest_delivery_date(timezone.now())
        on_date = parse_date(request.query_params.get("date", "")) or earliest
        return Response(
            {
                "earliest_delivery_date": earliest,
                "articles": [
                    {
                        "article": row["article"].id,
                        "article_code": row["article"].code,
                        "article_name": row["article"].name,
                        "unit_price": None if row["unit_price"] is None else str(row["unit_price"]),
                    }
                    for row in orders.orderable_articles(customer, on_date)
                ],
            }
        )


class EdiMessageViewSet(viewsets.ReadOnlyModelViewSet):
    """Journal des messages EDI. Les commerciaux peuvent simuler ou déposer un message."""

    queryset = EdiMessage.objects.select_related("customer", "order")
    serializer_class = EdiMessageSerializer
    permission_classes = [WriteRolesPermission]
    write_roles = SALES
    filterset_fields = ["status", "customer__code"]
    search_fields = ["message_id"]

    @action(detail=False, methods=["post"])
    def simulate(self, request):
        """Simule tout de suite la réception des commandes EDI du jour."""
        messages = edi.simulate_day()
        return Response(EdiMessageSerializer(messages, many=True).data, status=201)

    @action(detail=False, methods=["post"])
    def receive(self, request):
        """Dépose un message EDI (JSON) comme s'il venait d'une enseigne."""
        message = edi.integrate_message(request.data)
        return Response(EdiMessageSerializer(message).data, status=201)


# --- Expéditions (minimales, phase 5 ; la préparation viendra en 7b) -------------------


class ShipmentViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.filter(movement_type=MovementType.SHIPMENT).select_related(
        "lot__article", "customer_warehouse__customer"
    )
    permission_classes = [WriteRolesPermission]
    write_roles = WAREHOUSE
    filterset_fields = ["lot", "customer_warehouse", "customer_warehouse__customer__code"]

    def get_serializer_class(self):
        return ShipmentInputSerializer if self.action == "create" else ShipmentSerializer

    def create(self, request, *args, **kwargs):
        data = ShipmentInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        movement = services.record_shipment(user=request.user, **data.validated_data)
        return Response(ShipmentSerializer(movement).data, status=status.HTTP_201_CREATED)
