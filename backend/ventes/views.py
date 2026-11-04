"""API d'expédition (minimale) : /api/ventes/…"""

from decimal import Decimal

from rest_framework import mixins, serializers, status, viewsets
from rest_framework.response import Response

from comptes.permissions import WriteRolesPermission
from comptes.roles import Role
from referentiel.models import CustomerWarehouse, Location
from stocks.choices import MovementType
from stocks.models import Lot, StockMovement

from . import services


class ShipmentSerializer(serializers.ModelSerializer):
    lot_number = serializers.CharField(source="lot.number", read_only=True)
    article_code = serializers.CharField(source="lot.article.code", read_only=True)
    unit = serializers.CharField(source="lot.article.unit", read_only=True)
    customer_code = serializers.CharField(source="customer_warehouse.customer.code", read_only=True)
    warehouse_code = serializers.CharField(source="customer_warehouse.code", read_only=True)
    warehouse_name = serializers.CharField(source="customer_warehouse.name", read_only=True)
    quantity = serializers.SerializerMethodField()

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "reference",
            "created_at",
            "lot",
            "lot_number",
            "article_code",
            "unit",
            "quantity",
            "customer_code",
            "warehouse_code",
            "warehouse_name",
        ]

    def get_quantity(self, movement: StockMovement) -> str:
        return str(-movement.quantity)  # une expédition est une sortie : on l'affiche en positif


class ShipmentInputSerializer(serializers.Serializer):
    lot = serializers.PrimaryKeyRelatedField(queryset=Lot.objects.all())
    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0.001"))
    warehouse = serializers.PrimaryKeyRelatedField(queryset=CustomerWarehouse.objects.all())


class ShipmentViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    """Expéditions : /api/ventes/shipments/ (liste, déclaration)."""

    queryset = StockMovement.objects.filter(movement_type=MovementType.SHIPMENT).select_related(
        "lot__article", "customer_warehouse__customer"
    )
    permission_classes = [WriteRolesPermission]
    write_roles = [Role.ADMIN, Role.MAGASINIER]
    filterset_fields = ["lot", "customer_warehouse", "customer_warehouse__customer__code"]

    def get_serializer_class(self):
        return ShipmentInputSerializer if self.action == "create" else ShipmentSerializer

    def create(self, request, *args, **kwargs):
        data = ShipmentInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        movement = services.record_shipment(user=request.user, **data.validated_data)
        return Response(ShipmentSerializer(movement).data, status=status.HTTP_201_CREATED)
