"""API du pilotage : /api/pilotage/… (indicateurs du tableau de bord)."""

from datetime import timedelta

from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from comptes.access import can_see_amounts, dashboard_indicators
from comptes.permissions import WriteRolesPermission
from referentiel.models import Customer, Site

from . import indicators
from .search import search

# Période par défaut : les 4 dernières semaines, aujourd'hui compris
DEFAULT_DAYS = 28


def _dec(value) -> str | None:
    return None if value is None else str(value)


def _object_id(request: Request, name: str, model, label: str) -> int | None:
    raw = request.query_params.get(name)
    if not raw:
        return None
    if not raw.isdigit() or not model.objects.filter(pk=raw).exists():
        raise ValidationError({name: [f"{label} introuvable."]})
    return int(raw)


def _parameters(request: Request) -> dict:
    """Période (28 derniers jours par défaut), site et enseigne, vérifiés."""
    today = timezone.localdate()
    end = parse_date(request.query_params.get("end", "")) or today
    start = parse_date(request.query_params.get("start", "")) or end - timedelta(
        days=DEFAULT_DAYS - 1
    )
    if start > end:
        raise ValidationError({"start": ["La date de début est après la date de fin."]})
    if (end - start).days > 366:
        raise ValidationError({"start": ["Période limitée à un an."]})
    return {
        "start": start,
        "end": end,
        "site_id": _object_id(request, "site", Site, "Site"),
        "customer_id": _object_id(request, "customer", Customer, "Enseigne"),
    }


def _compute(request: Request, params: dict) -> tuple[list, list]:
    """Seulement les indicateurs du rôle (filtrés par le serveur, pas seulement à l'écran)."""
    filters = {
        "site_id": params["site_id"],
        "customer_id": params["customer_id"],
        "codes": dashboard_indicators(request.user),
    }
    return (
        indicators.compute(
            params["start"],
            params["end"],
            with_amounts=can_see_amounts(request.user),
            **filters,
        ),
        indicators.weekly(params["start"], params["end"], **filters),
    )


class IndicatorsView(APIView):
    """Les indicateurs de la fiche entreprise, avec leur évolution par semaine.

    Paramètres : start, end (AAAA-MM-JJ), site, customer (identifiants). Chaque rôle reçoit
    les indicateurs de son métier ; la direction les reçoit tous, avec les montants en euros.
    """

    permission_classes = [WriteRolesPermission]
    read_area = "pilotage"

    def get(self, request: Request) -> Response:
        params = _parameters(request)
        results, weeks = _compute(request, params)
        return Response(
            {
                "start": params["start"],
                "end": params["end"],
                "indicators": [
                    {
                        "code": item.code,
                        "label": item.label,
                        "unit": item.unit,
                        "definition": item.definition,
                        "filters": item.filters,
                        "value": _dec(item.value),
                        "target": item.target.label,
                        "target_min": _dec(item.target.minimum),
                        "target_max": _dec(item.target.maximum),
                        "status": item.status,
                        "detail": item.detail,
                    }
                    for item in results
                ],
                "weeks": [
                    {
                        "start": week["start"],
                        "end": week["end"],
                        "label": week["label"],
                        "values": {code: _dec(value) for code, value in week["values"].items()},
                    }
                    for week in weeks
                ],
            }
        )


class IndicatorsExportView(APIView):
    """Les mêmes indicateurs en fichier CSV, à ouvrir dans Excel."""

    permission_classes = [WriteRolesPermission]
    read_area = "pilotage"

    def get(self, request: Request) -> HttpResponse:
        params = _parameters(request)
        results, weeks = _compute(request, params)
        content = indicators.to_csv(params["start"], params["end"], results, weeks)
        response = HttpResponse(content, content_type="text/csv; charset=utf-8")
        filename = f"indicateurs-{params['start']:%Y%m%d}-{params['end']:%Y%m%d}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class SearchView(APIView):
    """Recherche globale : chaque famille de résultats est filtrée selon les droits de lecture."""

    permission_classes = [WriteRolesPermission]

    def get(self, request: Request) -> Response:
        return Response({"results": search(request.user, request.query_params.get("q", ""))})
