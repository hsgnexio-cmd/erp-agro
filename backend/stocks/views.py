"""API des stocks : /api/stocks/… (lecture seule en phase 3)."""

from decimal import Decimal

from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import viewsets

from comptes.permissions import WriteRolesPermission

from .models import Lot, StockMovement
from .serializers import LotSerializer, StockMovementSerializer


class LotViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        Lot.objects.select_related(
            "article", "supplier", "location__site", "reception_line__reception"
        )
        .annotate(
            current_quantity=Coalesce(
                Sum("movements__quantity"),
                Value(Decimal("0")),
                output_field=DecimalField(max_digits=14, decimal_places=3),
            )
        )
        .order_by("-created_at", "number")
    )
    serializer_class = LotSerializer
    permission_classes = [WriteRolesPermission]
    filterset_fields = [
        "status",
        "article",
        "article__code",
        "article__article_type",
        "supplier",
        "location",
        "location__site__code",
    ]
    search_fields = ["number", "supplier_lot_number", "article__code", "article__name"]
    ordering_fields = ["expiry_date", "created_at", "number"]


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.select_related("lot__article", "location", "user")
    serializer_class = StockMovementSerializer
    permission_classes = [WriteRolesPermission]
    filterset_fields = ["lot", "movement_type", "location", "reference"]
    search_fields = ["lot__number", "lot__article__code", "reference"]
