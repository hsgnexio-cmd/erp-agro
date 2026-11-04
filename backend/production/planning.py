"""Planning de la semaine par ligne : charge, capacité et ordre des allergènes."""

from datetime import date, timedelta
from decimal import Decimal

from qualite.services import compute_allergens
from referentiel.models import ProductionLine

from .models import OrderStatus, ProductionOrder

# 5 jours sur 7, deux équipes de 7 h 30 (fiche entreprise)
DAILY_CAPACITY_HOURS = Decimal("15")


def _fr(value: Decimal) -> str:
    """Nombre au format français : 15.6 → « 15,6 »."""
    return f"{value.normalize():f}".replace(".", ",")


def order_hours(order: ProductionOrder) -> Decimal:
    """Temps de ligne d'un OF = quantité ÷ cadence de la ligne."""
    if order.line is None:
        return Decimal("0")
    return (order.planned_quantity / order.line.capacity_per_hour).quantize(Decimal("0.1"))


def week_planning(week_start: date, site_code: str | None = None) -> dict:
    """OF de la semaine, ligne par ligne et jour par jour, avec les avertissements."""
    days = [week_start + timedelta(days=offset) for offset in range(7)]
    lines = ProductionLine.objects.filter(active=True).select_related("site").order_by("code")
    if site_code:
        lines = lines.filter(site__code=site_code)
    orders = (
        ProductionOrder.objects.filter(
            line__in=lines, planned_date__gte=days[0], planned_date__lte=days[-1]
        )
        .exclude(status=OrderStatus.CANCELLED)
        .select_related("article", "line")
        .order_by("line__code", "planned_date", "sequence", "id")
    )
    allergen_cache: dict[int, dict[str, str]] = {}

    def allergens_of(order) -> dict[str, str]:
        if order.article_id not in allergen_cache:
            allergen_cache[order.article_id] = {
                row["allergen"].code: row["allergen"].name
                for row in compute_allergens(order.article)
            }
        return allergen_cache[order.article_id]

    by_cell: dict[tuple[int, date], list] = {}
    for order in orders:
        by_cell.setdefault((order.line_id, order.planned_date), []).append(order)

    result_lines = []
    for line in lines:
        cells = []
        for day in days:
            cell_orders = by_cell.get((line.pk, day), [])
            hours = sum((order_hours(o) for o in cell_orders), Decimal("0"))
            warnings = []
            if hours > DAILY_CAPACITY_HOURS:
                capacity = _fr(DAILY_CAPACITY_HOURS)
                warnings.append(
                    f"Surcharge : {_fr(hours)} h prévues pour {capacity} h disponibles."
                )
            # Ordonnancement « sans allergène → avec allergènes »
            for previous, current in zip(cell_orders, cell_orders[1:], strict=False):
                missing = allergens_of(previous).keys() - allergens_of(current).keys()
                if missing:
                    names = ", ".join(sorted(allergens_of(previous)[code] for code in missing))
                    warnings.append(
                        f"{current.number} passe après {previous.number} qui contient : {names}. "
                        "Nettoyage renforcé requis (ou inverser l'ordre)."
                    )
            cells.append(
                {
                    "date": day,
                    "hours": hours,
                    "orders": [
                        {
                            "order": order,
                            "hours": order_hours(order),
                            "allergens": sorted(allergens_of(order).values()),
                        }
                        for order in cell_orders
                    ],
                    "warnings": warnings,
                }
            )
        result_lines.append({"line": line, "cells": cells})
    return {"days": days, "lines": result_lines, "capacity_hours": DAILY_CAPACITY_HOURS}
