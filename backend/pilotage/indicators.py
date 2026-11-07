"""Indicateurs de pilotage de la fiche entreprise (phase 8).

Tous les chiffres viennent des vues SQL du schéma `bi` (pilotage/sql/bi_views.sql) : le
tableau de bord et Power BI lisent exactement les mêmes données.

Filtres : la période s'applique à tous les indicateurs ; l'enseigne au taux de service et à
la fiabilité des prévisions ;
le site au rendement matière et à la couverture matières. Chaque indicateur indique les
filtres qu'il prend en compte.
"""

import csv
import io
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from django.db import connection
from django.db.models import Count, Q
from django.utils import timezone

from qualite.services import recall_impact
from referentiel.choices import ArticleType
from stocks.choices import MovementType
from stocks.models import Lot

ZERO = Decimal("0")


@dataclass
class Target:
    label: str
    minimum: Decimal | None = None
    maximum: Decimal | None = None

    def is_met(self, value: Decimal) -> bool:
        if self.minimum is not None and value < self.minimum:
            return False
        return self.maximum is None or value <= self.maximum


# Objectifs de la fiche entreprise (section 7)
TARGETS = {
    "service_rate": Target("≥ 98,5 %", minimum=Decimal("98.5")),
    "markdown": Target("≤ 1,5 % du CA", maximum=Decimal("1.5")),
    "finished_coverage": Target("2 à 4 jours", Decimal("2"), Decimal("4")),
    "material_coverage": Target("5 à 10 jours", Decimal("5"), Decimal("10")),
    "material_yield": Target("≥ 96 %", minimum=Decimal("96")),
    "oee": Target("≥ 70 %", minimum=Decimal("70")),
    "forecast_accuracy": Target("≥ 80 % à S-1", minimum=Decimal("80")),
    "reception_compliance": Target("≥ 97 %", minimum=Decimal("97")),
    "traceability": Target("≤ 5 min", maximum=Decimal("300")),
}


@dataclass
class Indicator:
    code: str
    label: str
    unit: str
    definition: str
    filters: list[str]
    value: Decimal | None = None
    detail: str = ""
    available: bool = True
    target: Target = field(init=False)

    def __post_init__(self):
        self.target = TARGETS[self.code]

    @property
    def status(self) -> str:
        if not self.available:
            return "indisponible"
        if self.value is None:
            return "sans_donnee"
        return "ok" if self.target.is_met(self.value) else "alerte"


def _one(sql: str, params: list) -> tuple:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone()


def _ratio(numerator, denominator, scale: int = 100, places: str = "0.1") -> Decimal | None:
    if not denominator:
        return None
    return (Decimal(numerator or 0) / Decimal(denominator) * scale).quantize(Decimal(places))


def _money(value) -> str:
    amount = f"{Decimal(value or 0):,.0f}".replace(",", " ")
    return f"{amount} €"


def _filter(column: str, value) -> tuple[str, list]:
    return (f" AND {column} = %s", [value]) if value is not None else ("", [])


# --- Calcul de chaque indicateur ------------------------------------------------------------


def service_rate(start: date, end: date, customer_id: int | None) -> tuple[Decimal | None, str]:
    where, params = _filter("customer_id", customer_id)
    on_time, ordered, orders = _one(
        "SELECT sum(delivered_on_time), sum(ordered), count(*) FROM bi.fact_service "
        f"WHERE is_counted AND requested_delivery_date BETWEEN %s AND %s{where}",
        [start, end, *params],
    )
    return _ratio(on_time, ordered), f"{orders} commande(s) livrable(s) sur la période"


def markdown(start: date, end: date) -> tuple[Decimal | None, str]:
    (lost,) = _one(
        "SELECT -sum(value) FROM bi.fact_stock_movement "
        "WHERE is_markdown AND date BETWEEN %s AND %s",
        [start, end],
    )
    (revenue,) = _one(
        "SELECT sum(amount) FROM bi.fact_sales WHERE date BETWEEN %s AND %s", [start, end]
    )
    value = _ratio(lost, revenue, places="0.01")
    return value, f"{_money(lost)} détruits ou donnés pour {_money(revenue)} de CA"


def _coverage(
    start: date, end: date, article_types: list[str], movement_type: str, site_id: int | None
) -> tuple[Decimal | None, str]:
    """Couverture en jours = stock disponible valorisé ÷ sorties moyennes valorisées par jour.

    Stock disponible = lots libérés ou en quarantaine (fabriqués ou reçus, en attente du
    contrôle qualité) ; les lots bloqués ne comptent pas.
    """
    where, params = _filter("site_id", site_id)
    (stock,) = _one(
        "SELECT sum(s.value) "
        "FROM bi.fact_stock_daily s JOIN bi.dim_article a USING (article_id) "
        f"WHERE s.date = %s AND s.lot_status IN ('libere', 'quarantaine') "
        f"AND a.article_type = ANY(%s){where}",
        [end, article_types, *params],
    )
    (outflow,) = _one(
        "SELECT -sum(m.value) FROM bi.fact_stock_movement m "
        "JOIN bi.dim_article a USING (article_id) "
        f"WHERE m.movement_type = %s AND a.article_type = ANY(%s) AND m.date BETWEEN %s AND %s"
        f"{where}",
        [movement_type, article_types, start, end, *params],
    )
    days = (end - start).days + 1
    daily = Decimal(outflow or 0) / days
    value = (Decimal(stock or 0) / daily).quantize(Decimal("0.1")) if daily else None
    detail = (
        f"Stock disponible de {_money(stock)} le {end:%d/%m}, sorties de {_money(daily)} par jour"
    )
    return value, detail


def material_yield(start: date, end: date, site_id: int | None) -> tuple[Decimal | None, str]:
    where, params = _filter("site_id", site_id)
    theoretical, actual, orders, low = _one(
        "SELECT sum(theoretical_mass), sum(actual_mass), count(*), "
        "count(*) FILTER (WHERE yield_pct < 96) FROM bi.fact_production_yield "
        f"WHERE date BETWEEN %s AND %s{where}",
        [start, end, *params],
    )
    return _ratio(theoretical, actual), f"{orders} OF terminé(s), dont {low} sous 96 %"


def forecast_accuracy(
    start: date, end: date, customer_id: int | None
) -> tuple[Decimal | None, str]:
    """Fiabilité à S-1 sur les semaines terminées qui touchent la période (vue
    bi.fact_forecast_accuracy, même règle que previsions.forecast.week_accuracy)."""
    where, params = _filter("customer_id", customer_id)
    abs_error, actual, weeks = _one(
        "SELECT sum(abs_error), sum(actual_quantity), count(DISTINCT week_start) "
        "FROM bi.fact_forecast_accuracy "
        f"WHERE is_complete AND week_start BETWEEN %s AND %s{where}",
        [start - timedelta(days=start.weekday()), end, *params],
    )
    if not actual:
        return None, "Aucune semaine terminée avec une prévision figée la semaine précédente"
    value = max(ZERO, (1 - Decimal(abs_error) / Decimal(actual)) * 100).quantize(Decimal("0.1"))
    detail = (
        f"{weeks} semaine(s) terminée(s) : écart de {abs_error:,.0f} unités pour "
        f"{actual:,.0f} commandées"
    ).replace(",", " ")
    return value, detail


def reception_compliance(start: date, end: date) -> tuple[Decimal | None, str]:
    compliant, total = _one(
        "SELECT count(*) FILTER (WHERE is_compliant), count(*) FROM bi.fact_reception "
        "WHERE date BETWEEN %s AND %s",
        [start, end],
    )
    return _ratio(compliant, total), f"{compliant} ligne(s) conforme(s) sur {total} reçue(s)"


def traceability(start: date, end: date) -> tuple[Decimal | None, str]:
    """Rappel « à blanc » mesuré maintenant sur le lot de matière le plus utilisé."""
    lot = (
        Lot.objects.filter(article__article_type=ArticleType.RAW_MATERIAL)
        .annotate(
            uses=Count("movements", filter=Q(movements__movement_type=MovementType.CONSUMPTION))
        )
        .filter(uses__gt=0)
        .order_by("-uses", "-id")
        .first()
    )
    if lot is None:
        return None, "Aucun lot de matière consommé : rien à tracer"
    impact = recall_impact(lot)
    count, worst = _one(
        "SELECT count(*), max(duration_ms) FROM bi.fact_recall WHERE date BETWEEN %s AND %s",
        [start, end],
    )
    seconds = (Decimal(impact.duration_ms) / 1000).quantize(Decimal("0.01"))
    detail = (
        f"Rappel à blanc sur le lot {lot.number} : {len(impact.lots)} lot(s) liés, "
        f"{len(impact.deliveries)} livraison(s)"
    )
    if count:
        detail += f" ; {count} rappel(s) lancé(s) sur la période (au plus {worst} ms)"
    return seconds, detail


# --- Assemblage ---------------------------------------------------------------------------


def compute(
    start: date,
    end: date,
    *,
    site_id: int | None = None,
    customer_id: int | None = None,
    with_traceability: bool = True,
) -> list[Indicator]:
    """Les neuf indicateurs de la fiche entreprise sur la période."""
    today = timezone.localdate()
    # Les stocks et sorties ne vont pas au-delà d'aujourd'hui
    stock_end = min(end, today)
    stock_start = min(start, stock_end)

    indicators = []

    def add(code, label, unit, definition, filters, computed=None, available=True, detail=""):
        indicator = Indicator(code, label, unit, definition, filters, available=available)
        if computed is not None:
            indicator.value, indicator.detail = computed
        else:
            indicator.detail = detail
        indicators.append(indicator)

    add(
        "service_rate", "Taux de service", "%",
        "Quantité livrée complète et à l'heure ÷ quantité commandée",
        ["période (livraison demandée)", "enseigne"],
        service_rate(start, end, customer_id),
    )  # fmt: skip
    add(
        "markdown", "Démarque", "% du CA",
        "Valeur détruite ou donnée (destructions, invendables) ÷ chiffre d'affaires",
        ["période"],
        markdown(start, end),
    )  # fmt: skip
    add(
        "finished_coverage", "Couverture produits finis", "jours",
        "Stock disponible de produits finis ÷ expéditions moyennes par jour (en valeur)",
        ["période (stock à la date de fin)"],
        _coverage(stock_start, stock_end, ["PF"], MovementType.SHIPMENT, None),
    )  # fmt: skip
    add(
        "material_coverage", "Couverture matières", "jours",
        "Stock disponible de matières premières ÷ consommations moyennes par jour (en valeur)",
        ["période (stock à la date de fin)", "site"],
        _coverage(stock_start, stock_end, ["MP"], MovementType.CONSUMPTION, site_id),
    )  # fmt: skip
    add(
        "material_yield", "Rendement matière", "%",
        "Consommation théorique (nomenclature, pertes comprises) ÷ consommation réelle",
        ["période (clôture de l'OF)", "site"],
        material_yield(start, end, site_id),
    )  # fmt: skip
    add(
        "oee", "TRS", "%", "Taux de rendement synthétique des lignes", [],
        available=False,
        detail="Non disponible : l'ERP n'enregistre ni les arrêts de ligne ni les cadences "
        "réelles.",
    )  # fmt: skip
    add(
        "forecast_accuracy", "Fiabilité des prévisions", "%",
        "1 − écart absolu ÷ commandes réelles, prévision figée la semaine précédente (S-1), "
        "par produit et par enseigne",
        ["période (semaines terminées)", "enseigne"],
        forecast_accuracy(start, end, customer_id),
    )  # fmt: skip
    add(
        "reception_compliance", "Conformité réception", "%",
        "Lignes de réception conformes ÷ lignes reçues",
        ["période"],
        reception_compliance(start, end),
    )  # fmt: skip
    if with_traceability:
        add(
            "traceability", "Délai de traçabilité", "s",
            "Durée du calcul complet d'un rappel (lots liés, stocks, clients livrés)",
            [],
            traceability(start, end),
        )  # fmt: skip
    return indicators


WEEKLY_CODES = (
    "service_rate",
    "markdown",
    "finished_coverage",
    "material_coverage",
    "material_yield",
    "forecast_accuracy",
    "reception_compliance",
)


def weekly(
    start: date, end: date, *, site_id: int | None = None, customer_id: int | None = None
) -> list[dict]:
    """Évolution semaine par semaine (semaines ISO, coupées aux bornes de la période)."""
    today = timezone.localdate()
    weeks = []
    monday = start - timedelta(days=start.weekday())
    while monday <= end and monday <= today:
        week_start, week_end = max(start, monday), min(end, monday + timedelta(days=6))
        values = {
            indicator.code: indicator.value
            for indicator in compute(
                week_start,
                week_end,
                site_id=site_id,
                customer_id=customer_id,
                with_traceability=False,
            )
            if indicator.code in WEEKLY_CODES
        }
        weeks.append(
            {
                "start": week_start,
                "end": week_end,
                "label": f"S{monday.isocalendar().week:02d}",
                "values": values,
            }
        )
        monday += timedelta(days=7)
    return weeks


# --- Export pour Excel ------------------------------------------------------------------

STATUS_LABELS = {
    "ok": "Objectif atteint",
    "alerte": "Hors objectif",
    "sans_donnee": "Pas de donnée",
    "indisponible": "Non disponible",
}


def _fr(value: Decimal | None) -> str:
    return "" if value is None else f"{value:f}".replace(".", ",")


def to_csv(start: date, end: date, results: list[Indicator], weeks: list[dict]) -> str:
    """Indicateurs et évolution par semaine, au format CSV lisible par Excel (« ; »)."""
    buffer = io.StringIO()
    buffer.write("﻿")  # indique à Excel que le fichier est en UTF-8 (accents)
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow([f"Indicateurs du {start:%d/%m/%Y} au {end:%d/%m/%Y}"])
    writer.writerow(["Indicateur", "Valeur", "Unité", "Objectif", "Statut", "Détail"])
    for item in results:
        writer.writerow(
            [item.label, _fr(item.value), item.unit, item.target.label,
             STATUS_LABELS[item.status], item.detail]
        )  # fmt: skip
    writer.writerow([])
    writer.writerow(["Évolution par semaine"])
    writer.writerow(["Indicateur", "Unité", *(f"{w['label']} ({w['start']:%d/%m})" for w in weeks)])
    for item in results:
        if item.code in WEEKLY_CODES:
            writer.writerow(
                [item.label, item.unit, *(_fr(w["values"].get(item.code)) for w in weeks)]
            )
    return buffer.getvalue()
