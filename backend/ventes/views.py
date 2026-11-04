"""API des ventes : /api/ventes/… (tarifs, commandes clients, EDI, préparation, expéditions)."""

from datetime import timedelta

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
from referentiel.models import Customer

from . import edi, orders, shipping
from .models import CustomerOrder, CustomerOrderLine, EdiMessage, SalePrice, Shipment
from .serializers import (
    CancelPreparationInputSerializer,
    CustomerOrderDetailSerializer,
    CustomerOrderInputSerializer,
    CustomerOrderSerializer,
    EdiMessageSerializer,
    PrepareInputSerializer,
    SalePriceSerializer,
    ShipInputSerializer,
    ShipmentDetailSerializer,
    ShipmentSerializer,
)

SALES = [Role.ADMIN, Role.COMMERCIAL]
WAREHOUSE = [Role.ADMIN, Role.MAGASINIER]


def _dec(value) -> str | None:
    return None if value is None else str(value)


class SalePriceViewSet(viewsets.ModelViewSet):
    queryset = SalePrice.objects.select_related("customer", "article")
    serializer_class = SalePriceSerializer
    permission_classes = [WriteRolesPermission]
    write_roles = SALES
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    filterset_fields = ["customer", "customer__code", "article"]
    search_fields = ["article__code", "article__name"]


SHIPMENT_QUERYSET = Shipment.objects.select_related(
    "order__customer", "order__warehouse", "prepared_by", "shipped_by"
).prefetch_related(
    "lines__lot__article",
    "lines__location",
    "pallets__lines__shipment_line__lot__article",
    "order__lines__article",
)


class CustomerOrderViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    queryset = CustomerOrder.objects.select_related(
        "customer", "warehouse", "edi_message", "created_by"
    ).prefetch_related(
        Prefetch(
            "lines",
            queryset=CustomerOrderLine.objects.select_related("article", "order").prefetch_related(
                "shipment_lines__shipment"
            ),
        ),
        "shipments",
    )
    permission_classes = [WriteRolesPermission]
    filterset_fields = ["status", "customer", "customer__code", "source", "requested_delivery_date"]
    search_fields = ["number", "customer_reference", "customer__name"]
    ordering_fields = ["received_at", "requested_delivery_date"]

    @property
    def write_roles(self):
        # Le commercial saisit et annule les commandes ; le magasinier les prépare
        return WAREHOUSE if self.action == "prepare" else SALES

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

    @action(detail=True, url_path="picking-proposal")
    def picking_proposal(self, request, pk=None):
        """Lots proposés en FEFO pour chaque ligne, hors lots trop courts pour l'enseigne."""
        order = self.get_object()
        rows = []
        for row in shipping.picking_proposal(order):
            line = row["order_line"]
            rows.append(
                {
                    "order_line": line.id,
                    "article": line.article_id,
                    "article_code": line.article.code,
                    "article_name": line.article.name,
                    "unit": line.article.unit,
                    "ordered": str(line.quantity),
                    "min_expiry_date": row["min_expiry_date"],
                    "missing": str(row["missing"]),
                    "lots": [
                        {
                            "lot": item.lot.id,
                            "lot_number": item.lot.number,
                            "expiry_date": item.lot.expiry_date,
                            "location": item.location.id,
                            "location_code": item.location.code,
                            "available": str(item.available),
                            "suggested": str(item.suggested),
                        }
                        for item in row["lots"]
                    ],
                    "too_short": [
                        {
                            "lot_number": item.lot.number,
                            "expiry_date": item.lot.expiry_date,
                            "location_code": item.location.code,
                            "available": str(item.available),
                        }
                        for item in row["too_short"]
                    ],
                }
            )
        return Response(
            {
                "order": order.id,
                "requested_delivery_date": order.requested_delivery_date,
                "min_remaining_shelf_life_pct": str(order.customer.min_remaining_shelf_life_pct),
                "lines": rows,
            }
        )

    @action(detail=True, methods=["post"])
    def prepare(self, request, pk=None):
        data = PrepareInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        shipment = shipping.prepare_order(
            self.get_object(), lines=data.validated_data["lines"], user=request.user
        )
        return Response(
            ShipmentDetailSerializer(SHIPMENT_QUERYSET.get(pk=shipment.pk)).data,
            status=status.HTTP_201_CREATED,
        )


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


class ShipmentViewSet(viewsets.ReadOnlyModelViewSet):
    """Bons de livraison. Ils naissent de la préparation d'une commande client."""

    queryset = SHIPMENT_QUERYSET
    permission_classes = [WriteRolesPermission]
    write_roles = WAREHOUSE
    filterset_fields = ["status", "order", "order__customer__code"]
    search_fields = ["number", "order__number", "pallets__sscc"]
    ordering_fields = ["prepared_at", "shipped_at"]

    def get_serializer_class(self):
        return ShipmentSerializer if self.action == "list" else ShipmentDetailSerializer

    def _detail(self, shipment) -> Response:
        return Response(ShipmentDetailSerializer(self.get_queryset().get(pk=shipment.pk)).data)

    @action(detail=True, methods=["post"])
    def ship(self, request, pk=None):
        data = ShipInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        shipment = shipping.ship_order(
            self.get_object(),
            carrier=data.validated_data["carrier"],
            temperature=data.validated_data["temperature"],
            user=request.user,
        )
        return self._detail(shipment)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        data = CancelPreparationInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        shipment = shipping.cancel_preparation(
            self.get_object(), reason=data.validated_data["reason"], user=request.user
        )
        return self._detail(shipment)


class ServiceRateView(APIView):
    """Taux de service par enseigne, sur les livraisons d'une période (par défaut : de J-29 à
    J+7, car les commandes livrées demain sont souvent déjà expédiées)."""

    permission_classes = [WriteRolesPermission]

    def get(self, request: Request) -> Response:
        today = timezone.localdate()
        end = parse_date(request.query_params.get("end", "")) or today + timedelta(days=7)
        start = parse_date(request.query_params.get("start", "")) or today - timedelta(days=29)
        if start > end:
            raise ValidationError({"start": ["La date de début est après la date de fin."]})
        customer = None
        if request.query_params.get("customer"):
            customer = Customer.objects.filter(pk=request.query_params["customer"]).first()
            if customer is None:
                raise ValidationError({"customer": ["Enseigne introuvable."]})
        report = shipping.service_rate(start=start, end=end, customer=customer)

        def row(data: dict) -> dict:
            return {
                "ordered": str(data["ordered"]),
                "on_time": str(data["on_time"]),
                "late": str(data["late"]),
                "missing": str(data["missing"]),
                "orders": data["orders"],
                "perfect_orders": data["perfect_orders"],
                "pending_orders": data["pending_orders"],
                "rate": _dec(data["rate"]),
                "below_target": data["below_target"],
            }

        return Response(
            {
                "start": report["start"],
                "end": report["end"],
                "target": str(report["target"]),
                "customers": [
                    {
                        "customer": data["customer"].id,
                        "customer_code": data["customer"].code,
                        "customer_name": data["customer"].name,
                        **row(data),
                    }
                    for data in report["customers"]
                ],
                "total": row(report["total"]),
                "issues": [
                    {
                        "order": issue["order"].id,
                        "order_number": issue["order"].number,
                        "customer_code": issue["order"].customer.code,
                        "requested_delivery_date": issue["order"].requested_delivery_date,
                        "problem": issue["problem"],
                        "ordered": str(issue["ordered"]),
                        "delivered": str(issue["delivered"]),
                        "shipped_at": issue["shipped_at"],
                    }
                    for issue in report["issues"]
                ],
            }
        )
