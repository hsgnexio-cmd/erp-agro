"""API de production : /api/production/… (ordres de fabrication, déclarations, planning)."""

from datetime import timedelta
from decimal import Decimal, InvalidOperation

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

from . import orders, planning
from .models import ProductionOrder
from .serializers import (
    DeclarationInputSerializer,
    DeclarationSerializer,
    OrderInputSerializer,
    OrderUpdateSerializer,
    ProductionOrderDetailSerializer,
    ProductionOrderSerializer,
)

PRODUCTION = [Role.ADMIN, Role.PRODUCTION]


class ProductionOrderViewSet(
    mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.ReadOnlyModelViewSet
):
    queryset = ProductionOrder.objects.select_related(
        "article", "site", "line", "output_location", "created_by"
    ).prefetch_related("declarations__lot", "declarations__user")
    permission_classes = [WriteRolesPermission]
    write_roles = PRODUCTION
    http_method_names = ["get", "post", "patch", "head", "options"]
    filterset_fields = ["status", "site__code", "line", "article", "planned_date"]
    search_fields = ["number", "article__code", "article__name"]
    ordering_fields = ["planned_date", "number"]

    def get_serializer_class(self):
        if self.action == "create":
            return OrderInputSerializer
        if self.action == "partial_update":
            return OrderUpdateSerializer
        return (
            ProductionOrderSerializer if self.action == "list" else ProductionOrderDetailSerializer
        )

    def _detail(self, order, status_code=status.HTTP_200_OK) -> Response:
        order = self.get_queryset().get(pk=order.pk)
        return Response(ProductionOrderDetailSerializer(order).data, status=status_code)

    def create(self, request, *args, **kwargs):
        data = OrderInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        order = orders.create_order(user=request.user, **data.validated_data)
        return self._detail(order, status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        data = OrderUpdateSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        return self._detail(orders.update_order(self.get_object(), **data.validated_data))

    @action(detail=True, methods=["post"])
    def launch(self, request, pk=None):
        return self._detail(orders.launch_order(self.get_object(), user=request.user))

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._detail(orders.cancel_order(self.get_object(), user=request.user))

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        return self._detail(orders.close_order(self.get_object(), user=request.user))

    @action(detail=True)
    def proposal(self, request, pk=None):
        """Lots à consommer, dans l'ordre FEFO : ?quantity=2000"""
        try:
            quantity = Decimal(request.query_params.get("quantity", ""))
        except InvalidOperation as exc:
            raise ValidationError({"quantity": ["Indique la quantité à produire."]}) from exc
        rows = orders.proposal(self.get_object(), quantity)
        return Response(
            [
                {
                    "component": row["need"].component.id,
                    "component_code": row["need"].component.code,
                    "component_name": row["need"].component.name,
                    "unit": row["need"].unit,
                    "need": str(row["need"].gross),
                    "missing": str(row["missing"]),
                    "lots": [
                        {
                            "lot": item["lot"].id,
                            "lot_number": item["lot"].number,
                            "expiry_date": item["lot"].expiry_date,
                            "location": item["location"].id,
                            "location_code": item["location"].code,
                            "available": str(item["available"]),
                            "suggested": str(item["suggested"]),
                        }
                        for item in row["lots"]
                    ],
                }
                for row in rows
            ]
        )

    @action(detail=True, methods=["post"])
    def declare(self, request, pk=None):
        data = DeclarationInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        declaration = orders.declare_production(
            self.get_object(), user=request.user, **data.validated_data
        )
        return Response(DeclarationSerializer(declaration).data, status=status.HTTP_201_CREATED)


class PlanningView(APIView):
    """Planning de la semaine : /api/production/planning/?week=2026-11-02&site=NAN"""

    permission_classes = [WriteRolesPermission]

    def get(self, request: Request) -> Response:
        day = parse_date(request.query_params.get("week", "")) or timezone.localdate()
        monday = day - timedelta(days=day.weekday())
        result = planning.week_planning(monday, request.query_params.get("site") or None)
        return Response(
            {
                "week_start": monday,
                "days": result["days"],
                "capacity_hours": str(result["capacity_hours"]),
                "lines": [
                    {
                        "line": row["line"].id,
                        "line_code": row["line"].code,
                        "line_name": row["line"].name,
                        "site_code": row["line"].site.code,
                        "capacity_per_hour": row["line"].capacity_per_hour,
                        "cells": [
                            {
                                "date": cell["date"],
                                "hours": str(cell["hours"]),
                                "warnings": cell["warnings"],
                                "orders": [
                                    {
                                        "id": item["order"].id,
                                        "number": item["order"].number,
                                        "article_code": item["order"].article.code,
                                        "quantity": str(item["order"].planned_quantity),
                                        "status": item["order"].status,
                                        "status_label": item["order"].get_status_display(),
                                        "sequence": item["order"].sequence,
                                        "hours": str(item["hours"]),
                                        "allergens": item["allergens"],
                                    }
                                    for item in cell["orders"]
                                ],
                            }
                            for cell in row["cells"]
                        ],
                    }
                    for row in result["lines"]
                ],
            }
        )
