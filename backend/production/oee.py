"""TRS des lignes de conditionnement (phase 10) : plages de marche, arrêts, rebuts.

Définitions (norme NF E60-182, décisions de la phase 10), par ligne et par période :
- temps d'ouverture = somme des plages de marche déclarées (début → fin de chaque passage
  d'OF sur la ligne, arrêts compris) ;
- temps requis = temps d'ouverture − arrêts planifiés (maintenance préventive, nettoyage
  planifié) ;
- temps de fonctionnement = temps requis − arrêts non planifiés (pannes, changements de série,
  manques, réglages) ;
- temps net = quantité produite (bonne + rebutée) ÷ cadence de la ligne ;
- temps utile = quantité bonne ÷ cadence.
Disponibilité = fonctionnement ÷ requis ; performance = net ÷ fonctionnement ;
qualité = utile ÷ net ; TRS = utile ÷ requis = disponibilité × performance × qualité.

Une plage de marche est comptée le jour de son début, un arrêt le jour de son début.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from referentiel.models import ProductionLine

from .models import (
    PLANNED_STOP_CATEGORIES,
    LineStop,
    ProductionDeclaration,
    ProductionOrder,
    StopCategory,
)

ZERO = Decimal("0")
MAX_RUN = timedelta(hours=16)  # deux équipes de 7 h 30, plus une marge
MAX_STOP = timedelta(hours=24)
OEE_TARGET = Decimal("70")


def _user(user):
    return user if user is not None and user.is_authenticated else None


def _hours(delta: timedelta) -> Decimal:
    return (Decimal(delta.total_seconds()) / 3600).quantize(Decimal("0.0001"))


# --- Plages de marche (déclarations) -------------------------------------------------------


def check_run(
    order: ProductionOrder,
    run_start: datetime | None,
    run_end: datetime | None,
    *,
    required: bool = False,
    exclude_declaration: int | None = None,
) -> list[str]:
    """Règles d'une plage de marche ; renvoie la liste des erreurs."""
    if run_start is None and run_end is None:
        if required and order.line_id:
            return ["Indique l'heure de début et de fin de marche de la ligne (calcul du TRS)."]
        return []
    if run_start is None or run_end is None:
        return ["Indique à la fois le début et la fin de marche."]
    if order.line_id is None:
        return ["Un semi-fini se prépare sans ligne : pas de plage de marche à saisir."]
    errors = []
    if run_end <= run_start:
        errors.append("La fin de marche doit être après le début.")
    elif run_end - run_start > MAX_RUN:
        errors.append("Une plage de marche ne dépasse pas 16 h (deux équipes).")
    if run_end > timezone.now():
        errors.append("La fin de marche ne peut pas être dans le futur.")
    overlap = (
        ProductionDeclaration.objects.filter(
            order__line_id=order.line_id, run_start__lt=run_end, run_end__gt=run_start
        )
        .exclude(pk=exclude_declaration)
        .select_related("order")
        .first()
    )
    if overlap:
        errors.append(
            f"La ligne {order.line.code} était déjà en marche pour {overlap.order.number} "
            f"de {timezone.localtime(overlap.run_start):%H:%M} à "
            f"{timezone.localtime(overlap.run_end):%H:%M}."
        )
    return errors


def check_scrap(quantity: Decimal | None, reason: str) -> list[str]:
    if quantity is None or quantity < 0:
        return ["La quantité rebutée ne peut pas être négative."]
    if quantity > 0 and not (reason or "").strip():
        return ["Indique le motif du rebut."]
    return []


# --- Arrêts de ligne -----------------------------------------------------------------------


@transaction.atomic
def record_stop(
    *,
    line: ProductionLine,
    started_at: datetime,
    ended_at: datetime,
    category: str,
    production_order: ProductionOrder | None = None,
    comment: str = "",
    user=None,
) -> LineStop:
    """Enregistre un arrêt de ligne (jamais modifié ensuite)."""
    errors = []
    if category not in StopCategory.values:
        errors.append("Cause d'arrêt inconnue.")
    if ended_at <= started_at:
        errors.append("La fin de l'arrêt doit être après son début.")
    elif ended_at - started_at > MAX_STOP:
        errors.append("Un arrêt se saisit jour par jour (24 h au plus).")
    if ended_at > timezone.now():
        errors.append("Un arrêt se saisit une fois terminé : la fin ne peut pas être future.")
    if production_order is not None and production_order.line_id != line.pk:
        errors.append(f"L'OF {production_order.number} n'est pas sur la ligne {line.code}.")
    # Verrou sur la ligne : deux saisies simultanées ne peuvent pas se chevaucher
    ProductionLine.objects.select_for_update().get(pk=line.pk)
    overlap = LineStop.objects.filter(
        line=line, cancelled_at__isnull=True, started_at__lt=ended_at, ended_at__gt=started_at
    ).first()
    if overlap:
        errors.append(
            f"Chevauchement avec l'arrêt « {overlap.get_category_display()} » de "
            f"{timezone.localtime(overlap.started_at):%H:%M} à "
            f"{timezone.localtime(overlap.ended_at):%H:%M}."
        )
    if errors:
        raise ValidationError(errors)
    return LineStop.objects.create(
        line=line,
        started_at=started_at,
        ended_at=ended_at,
        category=category,
        production_order=production_order,
        comment=comment.strip(),
        created_at=timezone.now(),
        created_by=_user(user),
    )


@transaction.atomic
def cancel_stop(stop: LineStop, *, reason: str, user=None) -> LineStop:
    stop = LineStop.objects.select_for_update().get(pk=stop.pk)
    if stop.cancelled_at is not None:
        raise ValidationError("Cet arrêt est déjà annulé.")
    if not (reason or "").strip():
        raise ValidationError({"reason": "Indique le motif de l'annulation."})
    stop.cancelled_at = timezone.now()
    stop.cancelled_by = _user(user)
    stop.cancel_reason = reason.strip()
    stop.save()
    return stop


# --- Calcul du TRS -----------------------------------------------------------------------


@dataclass
class LineTime:
    """Temps et quantités d'une ligne (sur un jour, ou cumulés sur une période)."""

    line: ProductionLine
    opening: Decimal = ZERO
    planned_stops: Decimal = ZERO
    unplanned_stops: Decimal = ZERO
    produced: Decimal = ZERO
    scrap: Decimal = ZERO
    # Cumuls des temps requis et de fonctionnement calculés jour par jour (jamais négatifs)
    required_total: Decimal = ZERO
    operating_total: Decimal = ZERO

    def add_day(self, day: LineTime) -> None:
        for name in ("opening", "planned_stops", "unplanned_stops", "produced", "scrap"):
            setattr(self, name, getattr(self, name) + getattr(day, name))
        required = max(ZERO, day.opening - day.planned_stops)
        self.required_total += required
        self.operating_total += max(ZERO, required - day.unplanned_stops)

    @property
    def required(self) -> Decimal:
        return self.required_total

    @property
    def operating(self) -> Decimal:
        return self.operating_total

    @property
    def net(self) -> Decimal:
        return self.produced / self.line.capacity_per_hour

    @property
    def useful(self) -> Decimal:
        return (self.produced - self.scrap) / self.line.capacity_per_hour


def ratio(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    if not denominator:
        return None
    return (numerator / denominator * 100).quantize(Decimal("0.1"))


@dataclass
class Rates:
    oee: Decimal | None
    availability: Decimal | None
    performance: Decimal | None
    quality: Decimal | None


def rates(required, operating, net, useful) -> Rates:
    return Rates(
        oee=ratio(useful, required),
        availability=ratio(operating, required),
        performance=ratio(net, operating),
        quality=ratio(useful, net),
    )


def _bounds(start: date, end: date) -> tuple[datetime, datetime]:
    to_dt = lambda day: timezone.make_aware(datetime.combine(day, datetime.min.time()))  # noqa: E731
    return to_dt(start), to_dt(end + timedelta(days=1))


def line_times(start: date, end: date, site_id: int | None = None) -> list[LineTime]:
    """Temps et quantités de chaque ligne entre deux dates (comprises), cumulés jour par jour
    (même calcul que la vue bi.fact_line_time)."""
    first, last = _bounds(start, end)
    lines = ProductionLine.objects.select_related("site").order_by("code")
    if site_id is not None:
        lines = lines.filter(site_id=site_id)
    lines = {line.pk: line for line in lines}
    days: dict[tuple[int, date], LineTime] = {}

    def day_of(line_id: int, moment: datetime) -> LineTime:
        key = (line_id, timezone.localtime(moment).date())
        if key not in days:
            days[key] = LineTime(lines[line_id])
        return days[key]

    declarations = ProductionDeclaration.objects.filter(
        order__line_id__in=lines, run_start__gte=first, run_start__lt=last
    ).select_related("lot", "order")
    for declaration in declarations:
        row = day_of(declaration.order.line_id, declaration.run_start)
        row.opening += _hours(declaration.run_end - declaration.run_start)
        row.produced += declaration.lot.initial_quantity + declaration.scrap_quantity
        row.scrap += declaration.scrap_quantity
    stops = LineStop.objects.filter(
        line_id__in=lines, cancelled_at__isnull=True, started_at__gte=first, started_at__lt=last
    )
    for stop in stops:
        row = day_of(stop.line_id, stop.started_at)
        duration = _hours(stop.ended_at - stop.started_at)
        if stop.is_planned:
            row.planned_stops += duration
        else:
            row.unplanned_stops += duration
    result = {pk: LineTime(line) for pk, line in lines.items()}
    for (line_id, _), day in sorted(days.items(), key=lambda item: item[0][1]):
        result[line_id].add_day(day)
    return list(result.values())


def report(start: date, end: date, site_id: int | None = None) -> dict:
    """TRS par ligne et global, avec le Pareto des arrêts non planifiés."""
    rows = [row for row in line_times(start, end, site_id) if row.opening or row.planned_stops]
    total = {"required": ZERO, "operating": ZERO, "net": ZERO, "useful": ZERO}
    for row in rows:
        total["required"] += row.required
        total["operating"] += row.operating
        total["net"] += row.net
        total["useful"] += row.useful
    first, last = _bounds(start, end)
    stops = LineStop.objects.filter(
        cancelled_at__isnull=True, started_at__gte=first, started_at__lt=last
    )
    if site_id is not None:
        stops = stops.filter(line__site_id=site_id)
    by_category: dict[str, list] = defaultdict(lambda: [ZERO, 0])
    for stop in stops:
        by_category[stop.category][0] += _hours(stop.ended_at - stop.started_at)
        by_category[stop.category][1] += 1
    unplanned_total = sum(
        (hours for category, (hours, _) in by_category.items()
         if category not in PLANNED_STOP_CATEGORIES),
        ZERO,
    )  # fmt: skip
    pareto = [
        {
            "category": category,
            "label": StopCategory(category).label,
            "planned": category in PLANNED_STOP_CATEGORIES,
            "hours": hours.quantize(Decimal("0.01")),
            "count": count,
            "share": None if category in PLANNED_STOP_CATEGORIES else ratio(hours, unplanned_total),
        }
        for category, (hours, count) in sorted(
            by_category.items(), key=lambda item: item[1][0], reverse=True
        )
    ]
    return {
        "lines": [
            {"row": row, "rates": rates(row.required, row.operating, row.net, row.useful)}
            for row in rows
        ],
        "total": rates(total["required"], total["operating"], total["net"], total["useful"]),
        "pareto": pareto,
    }


def recent_stops(start: date, end: date, site_id: int | None = None):
    first, last = _bounds(start, end)
    stops = LineStop.objects.filter(started_at__gte=first, started_at__lt=last).select_related(
        "line", "production_order", "created_by", "cancelled_by"
    )
    if site_id is not None:
        stops = stops.filter(line__site_id=site_id)
    return stops.order_by("-started_at", "-id")
