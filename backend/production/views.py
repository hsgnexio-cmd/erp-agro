"""API de fabrication (minimale) : /api/production/…"""

from decimal import Decimal

from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from comptes.permissions import WriteRolesPermission
from comptes.roles import Role
from referentiel.models import Article, Location
from stocks.models import Lot
from stocks.serializers import LotDetailSerializer
from stocks.views import LotViewSet

from . import services


class ConsumptionInputSerializer(serializers.Serializer):
    lot = serializers.PrimaryKeyRelatedField(queryset=Lot.objects.all())
    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3)


class ProductionInputSerializer(serializers.Serializer):
    article = serializers.PrimaryKeyRelatedField(queryset=Article.objects.all())
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0.001"))
    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    production_date = serializers.DateField(required=False)
    consumptions = ConsumptionInputSerializer(many=True)


class ProductionView(APIView):
    """Déclare une fabrication : POST /api/production/productions/"""

    permission_classes = [WriteRolesPermission]
    write_roles = [Role.ADMIN, Role.PRODUCTION]

    def post(self, request: Request) -> Response:
        data = ProductionInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        lot = services.record_production(user=request.user, **data.validated_data)
        lot = LotViewSet.queryset.get(pk=lot.pk)
        return Response(LotDetailSerializer(lot).data, status=status.HTTP_201_CREATED)
