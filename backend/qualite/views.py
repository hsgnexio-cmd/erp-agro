"""API qualité : /api/qualite/… (traçabilité, rappels, allergènes)."""

from django.http import HttpResponse
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from comptes.permissions import WriteRolesPermission
from comptes.roles import Role
from referentiel.models import Article
from stocks.models import Lot

from . import services
from .models import ProductRecall


def _lot_from_query(request: Request) -> Lot:
    number = request.query_params.get("lot", "").strip().upper()
    try:
        return Lot.objects.select_related("article").get(number=number)
    except Lot.DoesNotExist as exc:
        raise ValidationError({"lot": [f"Lot « {number} » introuvable."]}) from exc


def _node(node: services.TraceNode) -> dict:
    lot = node.lot
    return {
        "lot": lot.id,
        "lot_number": lot.number,
        "article_code": lot.article.code,
        "article_name": lot.article.name,
        "article_type": lot.article.article_type,
        "unit": lot.article.unit,
        "status": lot.status,
        "status_label": lot.get_status_display(),
        "expiry_date": lot.expiry_date,
        "quantity": None if node.quantity is None else str(node.quantity),
        "shipments": [
            {
                "customer_code": s["warehouse"].customer.code,
                "warehouse_code": s["warehouse"].code,
                "warehouse_name": s["warehouse"].name,
                "quantity": str(s["quantity"]),
                "last_shipped": s["last_shipped"],
            }
            for s in node.shipments
        ],
        "children": [_node(child) for child in node.children],
    }


class TraceabilityView(APIView):
    """Traçabilité d'un lot : /api/qualite/traceability/?lot=LR-261025-0001"""

    permission_classes = [WriteRolesPermission]

    def get(self, request: Request) -> Response:
        lot = _lot_from_query(request)
        return Response(
            {
                "upstream": _node(services.upstream(lot)),
                "downstream": _node(services.downstream(lot)),
            }
        )


class RecallSimulationView(APIView):
    """Simulation de rappel, sans rien modifier : /api/qualite/recall-simulation/?lot=…"""

    permission_classes = [WriteRolesPermission]

    def get(self, request: Request) -> Response:
        return Response(services.impact_to_dict(services.recall_impact(_lot_from_query(request))))


class RecallSerializer(serializers.ModelSerializer):
    origin_lot_number = serializers.CharField(source="origin_lot.number", read_only=True)
    origin_article_code = serializers.CharField(source="origin_lot.article.code", read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )
    blocked_lot_count = serializers.IntegerField(source="blocked_lots.count", read_only=True)

    class Meta:
        model = ProductRecall
        fields = [
            "id",
            "number",
            "origin_lot",
            "origin_lot_number",
            "origin_article_code",
            "reason",
            "created_at",
            "created_by_name",
            "blocked_lot_count",
        ]


class RecallDetailSerializer(RecallSerializer):
    class Meta(RecallSerializer.Meta):
        fields = [*RecallSerializer.Meta.fields, "snapshot"]


class LaunchRecallInputSerializer(serializers.Serializer):
    lot_number = serializers.CharField()
    reason = serializers.CharField(allow_blank=True)


class RecallViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    """Rappels lancés : /api/qualite/recalls/ ; lancement réservé à la qualité."""

    queryset = ProductRecall.objects.select_related("origin_lot__article", "created_by")
    permission_classes = [WriteRolesPermission]
    write_roles = [Role.ADMIN, Role.QUALITE]

    def get_serializer_class(self):
        if self.action == "create":
            return LaunchRecallInputSerializer
        return RecallSerializer if self.action == "list" else RecallDetailSerializer

    def create(self, request, *args, **kwargs):
        data = LaunchRecallInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        number = data.validated_data["lot_number"].strip().upper()
        try:
            lot = Lot.objects.get(number=number)
        except Lot.DoesNotExist as exc:
            raise ValidationError({"lot_number": [f"Lot « {number} » introuvable."]}) from exc
        recall = services.launch_recall(
            lot, reason=data.validated_data["reason"], user=request.user
        )
        return Response(RecallDetailSerializer(recall).data, status=status.HTTP_201_CREATED)

    @action(detail=True)
    def export(self, request, pk=None):
        """Liste des clients à prévenir, à ouvrir dans Excel."""
        recall = self.get_object()
        response = HttpResponse(services.recall_csv(recall), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{recall.number}-clients.csv"'
        return response


class AllergensView(APIView):
    """Allergènes calculés d'un article : /api/qualite/allergens/?article=12"""

    permission_classes = [WriteRolesPermission]

    def get(self, request: Request) -> Response:
        try:
            article = Article.objects.get(pk=request.query_params.get("article"))
        except (Article.DoesNotExist, ValueError) as exc:
            raise ValidationError({"article": ["Article introuvable."]}) from exc
        return Response(
            [
                {
                    "code": row["allergen"].code,
                    "name": row["allergen"].name,
                    "sources": row["sources"],
                }
                for row in services.compute_allergens(article)
            ]
        )
