"""API du pilotage : /api/pilotage/… (indicateurs du tableau de bord)."""

from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from comptes.permissions import WriteRolesPermission
from referentiel.models import Customer, Site

from . import indicators

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


class IndicatorsView(APIView):
    """Les indicateurs de la fiche entreprise, avec leur évolution par semaine.

    Paramètres : start, end (AAAA-MM-JJ), site, customer (identifiants). Consultable par
    tous les rôles.
    """

    permission_classes = [WriteRolesPermission]

    def get(self, request: Request) -> Response:
        today = timezone.localdate()
        end = parse_date(request.query_params.get("end", "")) or today
        start = parse_date(request.query_params.get("start", "")) or end - timedelta(
            days=DEFAULT_DAYS - 1
        )
        if start > end:
            raise ValidationError({"start": ["La date de début est après la date de fin."]})
        if (end - start).days > 366:
            raise ValidationError({"start": ["Période limitée à un an."]})
        site_id = _object_id(request, "site", Site, "Site")
        customer_id = _object_id(request, "customer", Customer, "Enseigne")

        results = indicators.compute(start, end, site_id=site_id, customer_id=customer_id)
        weeks = indicators.weekly(start, end, site_id=site_id, customer_id=customer_id)
        return Response(
            {
                "start": start,
                "end": end,
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
