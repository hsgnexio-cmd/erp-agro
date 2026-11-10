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
from previsions.forecast import week_label

from . import master_plan, oee, orders, planning
from .models import LineStop, MasterPlan, ProductionOrder
from .serializers import (
    DeclarationInputSerializer,
    DeclarationSerializer,
    LineStopInputSerializer,
    LineStopSerializer,
    MasterPlanSerializer,
    OrderInputSerializer,
    OrderUpdateSerializer,
    PlanAddArticleInputSerializer,
    PlanComputeInputSerializer,
    PlanLineInputSerializer,
    PlanQuantityInputSerializer,
    ProductionOrderDetailSerializer,
    ProductionOrderSerializer,
    StopCancelInputSerializer,
)

PRODUCTION = [Role.ADMIN, Role.PRODUCTION]


class ProductionOrderViewSet(
    mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.ReadOnlyModelViewSet
):
    queryset = ProductionOrder.objects.select_related(
        "article", "site", "line", "output_location", "created_by"
    ).prefetch_related("declarations__lot", "declarations__user")
    permission_classes = [WriteRolesPermission]
    read_area = "production"
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
        # Dans l'application, la plage de marche est obligatoire pour un produit fini (TRS)
        declaration = orders.declare_production(
            self.get_object(), user=request.user, require_run=True, **data.validated_data
        )
        return Response(DeclarationSerializer(declaration).data, status=status.HTTP_201_CREATED)


class PlanningView(APIView):
    """Planning de la semaine : /api/production/planning/?week=2026-11-02&site=NAN"""

    permission_classes = [WriteRolesPermission]
    read_area = "production"

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
                                "closed": cell["closed"],
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


# --- Plan de production hebdomadaire (phase 9b) ------------------------------------------


def _dec(value) -> str | None:
    return None if value is None else str(value)


def _plan_detail(plan: MasterPlan) -> dict:
    items = plan.items.select_related("article", "line__site").prefetch_related(
        "days__production_order__line"
    )
    return {
        "id": plan.id,
        "week": plan.week,
        "week_label": week_label(plan.week),
        "status": plan.status,
        "status_label": plan.get_status_display(),
        "forecast_version": plan.forecast_version.number if plan.forecast_version else None,
        "computed_at": plan.computed_at,
        "computed_by_name": plan.computed_by.username if plan.computed_by else "",
        "frozen_at": plan.frozen_at,
        "frozen_by_name": plan.frozen_by.username if plan.frozen_by else "",
        "days": master_plan.work_days(plan.week),
        "capacity_hours": str(planning.DAILY_CAPACITY_HOURS),
        "items": [
            {
                "article": item.article_id,
                "article_code": item.article.code,
                "article_name": item.article.name,
                "brand": "MDD" if item.article.brand_customer_id else "Brévanne",
                "line": item.line_id,
                "line_code": item.line.code,
                "forecast_quantity": _dec(item.forecast_quantity),
                "ordered_quantity": _dec(item.ordered_quantity),
                "demand": _dec(item.demand),
                "safety_days": _dec(item.safety_days),
                "safety_stock": _dec(item.safety_stock),
                "stock": _dec(item.stock),
                "open_orders": _dec(item.open_orders),
                "demand_before": _dec(item.demand_before),
                "projected_stock": _dec(item.projected_stock),
                "proposed_quantity": _dec(item.proposed_quantity),
                "days": [
                    {
                        "day": entry.day,
                        "quantity": _dec(entry.quantity),
                        "production_order": entry.production_order_id,
                        "production_order_number": (
                            entry.production_order.number if entry.production_order else None
                        ),
                        "deviation": master_plan.deviation(entry),
                        "closed": master_plan.closed_reason(entry.day, item.line),
                    }
                    for entry in sorted(item.days.all(), key=lambda value: value.day)
                ],
            }
            for item in items
        ],
        "load": [
            {
                "line": row["line"].id,
                "line_code": row["line"].code,
                "cells": [
                    {
                        "day": cell["day"],
                        "hours": str(cell["hours"]),
                        "overload": cell["overload"],
                        "closed": cell["closed"],
                    }
                    for cell in row["cells"]
                ],
            }
            for row in master_plan.line_load(plan)
        ],
    }


class MasterPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """Plans de production hebdomadaires : calcul, ajustements, gel à J-2."""

    queryset = MasterPlan.objects.select_related(
        "forecast_version", "computed_by", "frozen_by"
    ).order_by("-week")
    serializer_class = MasterPlanSerializer
    permission_classes = [WriteRolesPermission]
    read_area = "production"
    write_roles = PRODUCTION
    filterset_fields = ["week", "status"]

    def retrieve(self, request, *args, **kwargs):
        return Response(_plan_detail(self.get_object()))

    @action(detail=False, methods=["post"])
    def compute(self, request):
        data = PlanComputeInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        plan, skipped = master_plan.compute_plan(data.validated_data["week"], user=request.user)
        return Response({**_plan_detail(plan), "skipped": skipped}, status=status.HTTP_201_CREATED)

    def _apply(self, serializer_class, function):
        data = serializer_class(data=self.request.data)
        data.is_valid(raise_exception=True)
        plan = self.get_object()
        function(plan, **data.validated_data)
        return Response(_plan_detail(plan))

    @action(detail=True, methods=["post"], url_path="set-quantity")
    def set_quantity(self, request, pk=None):
        return self._apply(PlanQuantityInputSerializer, master_plan.set_quantity)

    @action(detail=True, methods=["post"], url_path="set-line")
    def set_line(self, request, pk=None):
        return self._apply(PlanLineInputSerializer, master_plan.set_line)

    @action(detail=True, methods=["post"], url_path="add-article")
    def add_article(self, request, pk=None):
        return self._apply(PlanAddArticleInputSerializer, master_plan.add_article)

    @action(detail=True, methods=["post"])
    def freeze(self, request, pk=None):
        plan = master_plan.freeze_plan(self.get_object(), user=request.user)
        return Response(_plan_detail(plan))


# --- Arrêts de ligne et TRS (phase 10) -------------------------------------------------


def _period(request: Request):
    today = timezone.localdate()
    end = parse_date(request.query_params.get("end", "")) or today
    start = parse_date(request.query_params.get("start", "")) or end - timedelta(days=27)
    if start > end:
        raise ValidationError({"start": ["La date de début est après la date de fin."]})
    site = request.query_params.get("site") or None
    if site is not None and not site.isdigit():
        raise ValidationError({"site": ["Site invalide."]})
    return start, end, int(site) if site else None


class LineStopViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    """Arrêts de ligne : saisie et annulation par la production, consultation pour tous."""

    queryset = LineStop.objects.select_related(
        "line", "production_order", "created_by", "cancelled_by"
    )
    serializer_class = LineStopSerializer
    permission_classes = [WriteRolesPermission]
    read_area = "production"
    write_roles = PRODUCTION
    filterset_fields = ["line", "category", "production_order"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list":
            start, end, site = _period(self.request)
            queryset = oee.recent_stops(start, end, site)
        return queryset

    def create(self, request, *args, **kwargs):
        data = LineStopInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        stop = oee.record_stop(user=request.user, **data.validated_data)
        return Response(LineStopSerializer(stop).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        data = StopCancelInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        stop = oee.cancel_stop(
            self.get_object(), reason=data.validated_data["reason"], user=request.user
        )
        return Response(LineStopSerializer(stop).data)


def _rates(value: oee.Rates) -> dict:
    return {
        "oee": _dec(value.oee),
        "availability": _dec(value.availability),
        "performance": _dec(value.performance),
        "quality": _dec(value.quality),
    }


def _hours(value) -> str:
    return str(value.quantize(Decimal("0.01")))


class OeeView(APIView):
    """TRS par ligne sur une période : /api/production/oee/?start=…&end=…&site=…"""

    permission_classes = [WriteRolesPermission]
    read_area = "production"

    def get(self, request: Request) -> Response:
        start, end, site = _period(request)
        result = oee.report(start, end, site)
        return Response(
            {
                "start": start,
                "end": end,
                "target": str(oee.OEE_TARGET),
                "total": _rates(result["total"]),
                "lines": [
                    {
                        "line": item["row"].line.id,
                        "line_code": item["row"].line.code,
                        "line_name": item["row"].line.name,
                        "site_code": item["row"].line.site.code,
                        "capacity_per_hour": item["row"].line.capacity_per_hour,
                        "opening_hours": _hours(item["row"].opening),
                        "planned_stop_hours": _hours(item["row"].planned_stops),
                        "unplanned_stop_hours": _hours(item["row"].unplanned_stops),
                        "required_hours": _hours(item["row"].required),
                        "produced": str(item["row"].produced),
                        "scrap": str(item["row"].scrap),
                        **_rates(item["rates"]),
                    }
                    for item in result["lines"]
                ],
                "pareto": [
                    {**row, "hours": str(row["hours"]), "share": _dec(row["share"])}
                    for row in result["pareto"]
                ],
            }
        )
