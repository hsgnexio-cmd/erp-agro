"""Données de démonstration de la production : OF, déclarations FEFO, rendements, planning.

Pour fabriquer des béchamels complètes, on réceptionne d'abord le beurre et la farine
encore attendus dans les commandes de démonstration.
"""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from achats import services as purchasing
from achats.models import PurchaseOrder
from referentiel.models import Article, Location, ProductionLine, Site
from stocks import services as stock_services
from stocks.choices import LotStatus

from . import orders
from .models import ProductionOrder

QUALITY_REASON = "Contrôle qualité à réception conforme"


def _receive_pending(today) -> int:
    """Réceptionne le beurre (Laiterie de la Mée) et la farine (Moulins de Brocéliande)."""
    pending = [
        ("FOU-003", "MP-LAI-BEURRE", "LM-B-2204", 55, Decimal("3.4")),
        ("FOU-009", "MP-SEC-FARINE", "MB-F-8812", 330, None),
    ]
    quarantine = {
        location.temperature_class: location
        for location in Location.objects.filter(code__startswith="MPE-QUAR")
    }
    received = 0
    for supplier, article_code, supplier_lot, shelf_days, temperature in pending:
        order = (
            PurchaseOrder.objects.filter(
                supplier__code=supplier,
                status__in=["envoyee", "partiellement_recue"],
                lines__article__code=article_code,
            )
            .order_by("order_date")
            .first()
        )
        if order is None:
            continue
        line = order.lines.get(article__code=article_code)
        remaining = line.quantity - line.received_quantity
        if remaining <= 0:
            continue
        day = today - timedelta(days=1)
        reception = purchasing.create_reception(
            order=order,
            location=quarantine[line.article.storage_temperature_class],
            delivery_note_number=f"BL-{supplier[-3:]}-{day:%m%d}",
            received_at=timezone.make_aware(datetime.combine(day, time(6, 45))),
            lines=[
                {
                    "order_line": line,
                    "quantity": remaining,
                    "supplier_lot_number": supplier_lot,
                    "expiry_date": day + timedelta(days=shelf_days),
                    "temperature": temperature,
                    "appearance_ok": True,
                }
            ],
        )
        lot = reception.lines.get().lot
        if lot.status == LotStatus.QUARANTINE:
            stock_services.release_lot(lot, reason=QUALITY_REASON)
        received += 1
    return received


def _supply_factory(article_code: str, location: Location, quantity: Decimal) -> None:
    """Amène à l'usine le stock libéré nécessaire, lot qui périme le premier d'abord."""
    missing = quantity - sum(
        (
            line.available
            for line in stock_services.fefo_plan(
                Article.objects.get(code=article_code), location.site, orders.UNLIMITED
            ).lines
        ),
        Decimal("0"),
    )
    if missing <= 0:
        return
    article = Article.objects.get(code=article_code)
    warehouse = Site.objects.get(code="MPE")
    for line in stock_services.fefo_plan(article, warehouse, missing).lines:
        stock_services.transfer(
            line.lot,
            from_location=line.location,
            to_location=location,
            quantity=line.take,
            reason="Approvisionnement usine",
        )


def _declare(order: ProductionOrder, quantity: Decimal, factor: Decimal = Decimal("1")) -> None:
    """Déclare avec les lots proposés par le FEFO (× factor pour simuler des pertes)."""
    consumptions = []
    for row in orders.proposal(order, quantity):
        for item in row["lots"]:
            if item["suggested"] > 0:
                consumptions.append(
                    {
                        "lot": item["lot"],
                        "location": item["location"],
                        "quantity": min(item["suggested"] * factor, item["available"]).quantize(
                            Decimal("0.001")
                        ),
                    }
                )
    orders.declare_production(order, quantity=quantity, consumptions=consumptions)


@transaction.atomic
def load_demo_data() -> dict[str, int | str]:
    if ProductionOrder.objects.exists():
        return {"production": "déjà présente, non modifiée"}

    today = timezone.localdate()
    nantes = Site.objects.get(code="NAN")
    loc = {location.code: location for location in Location.objects.all()}
    art = {
        article.code: article for article in Article.objects.filter(article_type__in=["SF", "PF"])
    }
    lines = {line.code: line for line in ProductionLine.objects.all()}

    received = _receive_pending(today)
    for code, location, quantity in (
        ("MP-LAI-LAIT", "NAN-CF-MP", Decimal("160")),
        ("MP-LAI-CREME35", "NAN-CF-MP", Decimal("25")),
        ("MP-LAI-BEURRE", "NAN-CF-MP", Decimal("20")),
        ("MP-SEC-FARINE", "NAN-AMB-MP", Decimal("20")),
    ):
        _supply_factory(code, loc[location], quantity)

    # Deux béchamels terminées : l'une conforme, l'autre avec 6 % de surconsommation
    normal = orders.create_order(
        article=art["SF-BECHAMEL"], planned_quantity=Decimal("100"),
        planned_date=today - timedelta(days=1), site=nantes,
    )  # fmt: skip
    orders.launch_order(normal)
    _declare(normal, Decimal("100"))
    orders.close_order(normal)

    wasteful = orders.create_order(
        article=art["SF-BECHAMEL"], planned_quantity=Decimal("100"), planned_date=today,
        site=nantes, comment="Fuite sur la cuve de cuisson signalée par l'équipe du matin",
    )  # fmt: skip
    orders.launch_order(wasteful)
    _declare(wasteful, Decimal("100"), factor=Decimal("1.06"))
    orders.close_order(wasteful)

    # Lasagnes lancées aujourd'hui (pas encore déclarées)
    launched = orders.create_order(
        article=art["PF-PAT-LASBOL-BRE-300"], planned_quantity=Decimal("2000"),
        planned_date=today, line=lines["L1"],
    )  # fmt: skip
    orders.launch_order(launched)

    # Planning : allergènes dans le mauvais ordre sur L1, surcharge sur L3
    planned = [
        ("PF-PAT-LASBOL-ENS1-300", "1500", 1, "L1", 1),
        ("PF-PAT-COQJAM-BRE-300", "1200", 1, "L1", 2),
        ("PF-GRA-HACHIS-BRE-1000", "8000", 2, "L3", 1),
        ("PF-GRA-GRADAU-BRE-1000", "6000", 2, "L3", 2),
        ("PF-GRA-HACHIS-ENS5-300", "3000", 2, "L4", 1),
    ]
    for code, quantity, days, line, sequence in planned:
        orders.create_order(
            article=art[code], planned_quantity=Decimal(quantity),
            planned_date=today + timedelta(days=days), line=lines[line], sequence=sequence,
        )  # fmt: skip
    cancelled = orders.create_order(
        article=art["PF-SAU-BOEBOU-BRE-300"], planned_quantity=Decimal("1000"),
        planned_date=today + timedelta(days=1), line=lines["L5"],
        comment="Annulé : bœuf détruit (rupture de la chaîne du froid)",
    )  # fmt: skip
    orders.cancel_order(cancelled)

    return {
        "réceptions complétées": received,
        "ordres de fabrication": ProductionOrder.objects.count(),
    }
