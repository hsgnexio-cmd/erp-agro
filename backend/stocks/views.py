"""API des stocks : /api/stocks/…"""

from decimal import Decimal, InvalidOperation

from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.utils.dateparse import parse_date
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from comptes.permissions import WriteRolesPermission
from comptes.roles import Role
from referentiel.models import Article, Site

from . import services
from .choices import LotStatus
from .models import Lot, StockMovement
from .serializers import (
    CorrectionInputSerializer,
    LotDetailSerializer,
    LotSerializer,
    StatusChangeInputSerializer,
    StockMovementSerializer,
    TransferInputSerializer,
)

QUALITY = [Role.ADMIN, Role.QUALITE]
WAREHOUSE = [Role.ADMIN, Role.MAGASINIER]


class LotViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        Lot.objects.select_related(
            "article", "supplier", "location__site", "reception_line__reception"
        )
        .prefetch_related("status_changes__user")
        .annotate(
            current_quantity=Coalesce(
                Sum("movements__quantity"),
                Value(Decimal("0")),
                output_field=DecimalField(max_digits=14, decimal_places=3),
            )
        )
        .order_by("-created_at", "number")
    )
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

    @property
    def write_roles(self):
        # Règle 6 : seule la qualité change les statuts ; le magasinier déplace le stock
        return WAREHOUSE if self.action == "transfer" else QUALITY

    def get_serializer_class(self):
        return LotDetailSerializer if self.action != "list" else LotSerializer

    def _detail(self, lot: Lot) -> Response:
        return Response(LotDetailSerializer(self.get_queryset().get(pk=lot.pk)).data)

    def _change_status(self, request: Request, new_status: str) -> Response:
        data = StatusChangeInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        lot = services.change_status(
            self.get_object(), new_status, user=request.user, reason=data.validated_data["reason"]
        )
        return self._detail(lot)

    @action(detail=True, methods=["post"])
    def release(self, request, pk=None):
        """Quarantaine → libéré (ou débloque un lot bloqué, avec un motif)."""
        return self._change_status(request, LotStatus.RELEASED)

    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        return self._change_status(request, LotStatus.BLOCKED)

    @action(detail=True, methods=["post"], url_path="destroy")
    def destroy_lot(self, request, pk=None):
        return self._change_status(request, LotStatus.DESTROYED)

    @action(detail=True, methods=["post"])
    def transfer(self, request, pk=None):
        data = TransferInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        lot = self.get_object()
        services.transfer(lot, user=request.user, **data.validated_data)
        return self._detail(lot)


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.select_related("lot__article", "location", "user")
    serializer_class = StockMovementSerializer
    permission_classes = [WriteRolesPermission]
    write_roles = WAREHOUSE
    filterset_fields = ["lot", "movement_type", "location", "reference"]
    search_fields = ["lot__number", "lot__article__code", "reference"]

    @action(detail=True, methods=["post"])
    def correct(self, request, pk=None):
        """Corrige un mouvement de réception par un mouvement inverse."""
        data = CorrectionInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        correction = services.correct_movement(
            self.get_object(), user=request.user, **data.validated_data
        )
        return Response(StockMovementSerializer(correction).data, status=201)


def _decimal(value: str | None, field: str) -> Decimal:
    try:
        return Decimal(value or "")
    except InvalidOperation as exc:
        raise ValidationError({field: "Nombre invalide."}) from exc


class FefoView(APIView):
    """Lots à utiliser en priorité.

    Exemple : /api/stocks/fefo/?article=MP-LAI-CREME35&site=MPE&quantity=500
    """

    permission_classes = [WriteRolesPermission]

    def get(self, request: Request) -> Response:
        params = request.query_params
        try:
            article = Article.objects.get(code=params.get("article", "").strip().upper())
        except Article.DoesNotExist as exc:
            raise ValidationError({"article": "Article introuvable."}) from exc
        try:
            site = Site.objects.get(code=params.get("site", "").strip().upper())
        except Site.DoesNotExist as exc:
            raise ValidationError({"site": "Site introuvable."}) from exc
        plan = services.fefo_plan(
            article,
            site,
            _decimal(params.get("quantity"), "quantity"),
            min_expiry_date=parse_date(params.get("min_expiry_date", "")),
        )
        return Response(
            {
                "article_code": article.code,
                "unit": article.unit,
                "site_code": site.code,
                "requested": str(plan.requested),
                "covered": str(plan.covered),
                "missing": str(plan.missing),
                "lines": [
                    {
                        "lot": line.lot.id,
                        "lot_number": line.lot.number,
                        "expiry_date": line.lot.expiry_date,
                        "date_type": line.lot.date_type,
                        "location_code": line.location.code,
                        "available": str(line.available),
                        "take": str(line.take),
                    }
                    for line in plan.lines
                ],
            }
        )


class StockSummaryView(APIView):
    """État des stocks par article et par site : /api/stocks/summary/?site=MPE&article_type=MP"""

    permission_classes = [WriteRolesPermission]

    def get(self, request: Request) -> Response:
        params = request.query_params
        site = Site.objects.filter(code=params.get("site", "").upper()).first()
        rows = services.stock_summary(
            site=site,
            article_type=params.get("article_type") or None,
            search=params.get("search", "").strip(),
        )
        for row in rows:
            for key in ("released", "quarantine", "blocked", "total"):
                row[key] = str(row[key])
        return Response(rows)
