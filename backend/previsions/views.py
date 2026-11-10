"""API des prévisions : /api/previsions/… (prévision du moment, versions, promotions,
corrections, fiabilité à S-1)."""

from datetime import timedelta

from django.db.models import Count, Sum
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

from . import forecast
from .models import ForecastAdjustment, ForecastVersion, Promotion
from .serializers import (
    AdjustmentInputSerializer,
    ForecastAdjustmentSerializer,
    ForecastVersionSerializer,
    PromotionInputSerializer,
    PromotionSerializer,
    ReasonInputSerializer,
    VersionInputSerializer,
)

SALES = [Role.ADMIN, Role.COMMERCIAL]


def _dec(value) -> str | None:
    return None if value is None else str(value)


def _customer_param(request: Request) -> int | None:
    value = request.query_params.get("customer")
    if not value:
        return None
    if not value.isdigit():
        raise ValidationError({"customer": ["Enseigne invalide."]})
    return int(value)


def _weeks(weeks) -> list[dict]:
    return [{"week": week, "label": forecast.week_label(week)} for week in weeks]


class ForecastView(APIView):
    """Prévision du moment (non figée), par enseigne × produit, sur les 8 semaines à venir."""

    permission_classes = [WriteRolesPermission]
    read_area = "previsions"

    def get(self, request: Request) -> Response:
        customer_id = _customer_param(request)
        now = timezone.now()
        weeks = forecast.horizon(now)
        computed = {
            (row.customer.pk, row.article.pk, row.week): row
            for row in forecast.compute(now, customer_id)
        }
        rows = []
        for customer, article in forecast.forecastable_pairs(customer_id):
            cells = []
            for week in weeks:
                row = computed.get((customer.pk, article.pk, week))
                adjustment = row.adjustment if row else None
                cells.append(
                    {
                        "week": week,
                        "base": _dec(row.base_quantity if row else forecast.ZERO),
                        "promotion": row.promotion.pk if row and row.promotion else None,
                        "promo_coefficient": _dec(row.promo_coefficient if row else None),
                        "promo_quantity": _dec(row.promo_quantity if row else None),
                        "adjustment": None
                        if adjustment is None
                        else {
                            "id": adjustment.pk,
                            "quantity": _dec(adjustment.quantity),
                            "reason": adjustment.reason,
                            "created_at": adjustment.created_at,
                            "created_by_name": adjustment.created_by.username
                            if adjustment.created_by
                            else "",
                        },
                        "quantity": _dec(row.quantity if row else forecast.ZERO),
                    }
                )
            rows.append(
                {
                    "customer": customer.pk,
                    "customer_code": customer.code,
                    "article": article.pk,
                    "article_code": article.code,
                    "article_name": article.name,
                    "cells": cells,
                }
            )
        return Response(
            {
                "computed_at": now,
                "current_week": forecast.current_week(now),
                "weeks": _weeks(weeks),
                "rows": rows,
            }
        )


class ForecastVersionViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    """Versions figées. Le commercial peut figer une version à la demande."""

    queryset = (
        ForecastVersion.objects.select_related("created_by")
        .annotate(line_count=Count("lines"), total_quantity=Sum("lines__quantity"))
        .order_by("-created_at", "-id")
    )
    serializer_class = ForecastVersionSerializer
    permission_classes = [WriteRolesPermission]
    read_area = "previsions"
    write_roles = SALES
    filterset_fields = ["source"]

    def create(self, request, *args, **kwargs):
        data = VersionInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        version = forecast.create_version(user=request.user, **data.validated_data)
        return Response(
            ForecastVersionSerializer(self.get_queryset().get(pk=version.pk)).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        version = self.get_object()
        lines = version.lines.select_related("customer", "article").order_by(
            "customer__code", "article__code", "week"
        )
        customer_id = _customer_param(request)
        if customer_id is not None:
            lines = lines.filter(customer_id=customer_id)
        data = ForecastVersionSerializer(version).data
        data["lines"] = [
            {
                "customer_code": line.customer.code,
                "article_code": line.article.code,
                "article_name": line.article.name,
                "week": line.week,
                "week_label": forecast.week_label(line.week),
                "base_quantity": _dec(line.base_quantity),
                "promo_coefficient": _dec(line.promo_coefficient),
                "adjusted": line.adjustment_id is not None,
                "quantity": _dec(line.quantity),
            }
            for line in lines
        ]
        return Response(data)


class PromotionViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Promotion.objects.select_related("customer", "article", "created_by", "cancelled_by")
    serializer_class = PromotionSerializer
    permission_classes = [WriteRolesPermission]
    read_area = "previsions"
    write_roles = SALES
    filterset_fields = ["customer", "article"]

    def create(self, request, *args, **kwargs):
        data = PromotionInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        promotion = forecast.create_promotion(user=request.user, **data.validated_data)
        return Response(
            PromotionSerializer(self.get_queryset().get(pk=promotion.pk)).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        data = ReasonInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        promotion = forecast.cancel_promotion(
            self.get_object(), reason=data.validated_data["reason"], user=request.user
        )
        return Response(PromotionSerializer(self.get_queryset().get(pk=promotion.pk)).data)


class ForecastAdjustmentViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    """Journal des corrections manuelles (jamais modifiées ni supprimées)."""

    queryset = ForecastAdjustment.objects.select_related("customer", "article", "created_by")
    serializer_class = ForecastAdjustmentSerializer
    permission_classes = [WriteRolesPermission]
    read_area = "previsions"
    write_roles = SALES
    filterset_fields = ["customer", "article", "week"]

    def create(self, request, *args, **kwargs):
        data = AdjustmentInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        adjustment = forecast.create_adjustment(user=request.user, **data.validated_data)
        return Response(
            ForecastAdjustmentSerializer(self.get_queryset().get(pk=adjustment.pk)).data,
            status=status.HTTP_201_CREATED,
        )


class AccuracyView(APIView):
    """Fiabilité à S-1, semaine par semaine (par défaut : les 8 dernières semaines)."""

    permission_classes = [WriteRolesPermission]
    read_area = "previsions"

    def get(self, request: Request) -> Response:
        today = timezone.localdate()
        end = parse_date(request.query_params.get("end", "")) or today
        start = parse_date(request.query_params.get("start", "")) or end - timedelta(days=55)
        if start > end:
            raise ValidationError({"start": ["La date de début est après la date de fin."]})
        results = forecast.accuracy_by_week(start, end, _customer_param(request))
        overall = forecast.overall_accuracy(results)
        return Response(
            {
                "start": start,
                "end": end,
                "target": str(forecast.ACCURACY_TARGET),
                "accuracy": _dec(overall),
                "weeks": [
                    {
                        "week": result.week,
                        "label": forecast.week_label(result.week),
                        "version_number": result.version.number,
                        "version_created_at": result.version.created_at,
                        "forecast": _dec(result.forecast),
                        "actual": _dec(result.actual),
                        "abs_error": _dec(result.abs_error),
                        "accuracy": _dec(result.accuracy),
                        "complete": result.complete,
                    }
                    for result in results
                ],
            }
        )
