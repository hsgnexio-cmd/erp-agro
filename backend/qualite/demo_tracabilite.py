"""Données de démonstration de la traçabilité : fabrications et expéditions.

Crème CB-0412 → béchamel → lasagnes (Brévanne et MDD Hyper Atlantique) → 3 enseignes.
Le gratin dauphinois est fait avec l'autre lot de crème (CB-0419) : il ne doit PAS
apparaître dans un rappel du lot CB-0412. C'est le scénario de référence de CLAUDE.md.
"""

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from production.services import record_production
from referentiel.models import Article, CustomerWarehouse, Location
from stocks import services as stock_services
from stocks.choices import LotStatus, MovementType
from stocks.models import Lot, StockMovement
from ventes.services import record_shipment

QUALITY_REASON = "Contrôles libératoires conformes"


def _released(lot: Lot) -> Lot:
    if lot.status == LotStatus.QUARANTINE:
        return stock_services.release_lot(lot, reason=QUALITY_REASON)
    return lot


def _ensure_at(lot: Lot, location: Location, quantity: Decimal) -> None:
    """Approvisionne l'emplacement si besoin, depuis l'endroit où le lot a le plus de stock."""
    missing = quantity - stock_services.quantity_at(lot, location)
    if missing <= 0:
        return
    sources = [
        (loc, qty) for loc, qty in stock_services.stock_by_location(lot) if loc.pk != location.pk
    ]
    source, _ = max(sources, key=lambda item: item[1])
    stock_services.transfer(
        lot, from_location=source, to_location=location, quantity=missing,
        reason="Approvisionnement atelier",
    )  # fmt: skip


@transaction.atomic
def load_demo_data() -> dict[str, int | str]:
    if StockMovement.objects.filter(movement_type=MovementType.CONSUMPTION).exists():
        return {"traçabilité": "déjà présente, non modifiée"}
    lots = {lot.supplier_lot_number: lot for lot in Lot.objects.filter(supplier__isnull=False)}
    needed = ("CB-0412", "CB-0419", "LM-5541", "CB-E-118")
    if not all(code in lots for code in needed):
        return {"traçabilité": "lots de démonstration des achats absents"}

    today = timezone.localdate()
    loc = {location.code: location for location in Location.objects.all()}
    art = {article.code: article for article in Article.objects.all()}
    workshop, semi_finished_room = loc["NAN-CF-MP"], loc["NAN-CF-SF"]
    cream, other_cream = lots["CB-0412"], lots["CB-0419"]
    milk, emmental = _released(lots["LM-5541"]), lots["CB-E-118"]

    for lot, quantity in ((cream, "60"), (other_cream, "60"), (milk, "185"), (emmental, "45")):
        _ensure_at(lot, workshop, Decimal(quantity))

    # 1. Béchamel avec la crème CB-0412
    bechamel = record_production(
        article=art["SF-BECHAMEL"],
        quantity=Decimal("200"),
        location=semi_finished_room,
        production_date=today - timedelta(days=2),
        consumptions=[
            {"lot": cream, "location": workshop, "quantity": Decimal("60")},
            {"lot": milk, "location": workshop, "quantity": Decimal("140")},
        ],
    )
    bechamel = _released(bechamel)

    # 2. Lasagnes (marque Brévanne et MDD Hyper Atlantique) avec cette béchamel
    finished = {}
    for code, quantity, bechamel_kg, emmental_kg in (
        ("PF-PAT-LASBOL-BRE-300", "1000", "90", "30"),
        ("PF-PAT-LASBOL-ENS1-300", "500", "45", "15"),
    ):
        finished[code] = record_production(
            article=art[code],
            quantity=Decimal(quantity),
            location=loc["PFN-QUAR"],
            production_date=today - timedelta(days=1),
            consumptions=[
                {"lot": bechamel, "location": semi_finished_room, "quantity": Decimal(bechamel_kg)},
                {"lot": emmental, "location": workshop, "quantity": Decimal(emmental_kg)},
            ],
        )
    # 3. Gratin dauphinois avec l'AUTRE lot de crème (non concerné par un rappel de CB-0412)
    finished["PF-GRA-GRADAU-BRE-1000"] = record_production(
        article=art["PF-GRA-GRADAU-BRE-1000"],
        quantity=Decimal("300"),
        location=loc["PFN-QUAR"],
        production_date=today - timedelta(days=1),
        consumptions=[
            {"lot": other_cream, "location": workshop, "quantity": Decimal("60")},
            {"lot": milk, "location": workshop, "quantity": Decimal("45")},
        ],
    )

    # Libération et rangement des produits finis à la plateforme
    for code, lot in finished.items():
        lot = finished[code] = _released(lot)
        stock_services.transfer(
            lot, from_location=loc["PFN-QUAR"], to_location=loc["PFN-FRAIS-A"],
            quantity=lot.initial_quantity, reason="Rangement après libération",
        )  # fmt: skip

    # 4. Expéditions vers les enseignes
    warehouses = {w.code: w for w in CustomerWarehouse.objects.all()}
    shipments = [
        ("PF-PAT-LASBOL-BRE-300", "400", "ENS1-E01"),
        ("PF-PAT-LASBOL-BRE-300", "300", "ENS2-E03"),
        ("PF-PAT-LASBOL-BRE-300", "150", "ENS3-E02"),
        ("PF-PAT-LASBOL-ENS1-300", "300", "ENS1-E02"),
        ("PF-GRA-GRADAU-BRE-1000", "150", "ENS2-E01"),
    ]
    for code, quantity, warehouse in shipments:
        record_shipment(
            lot=finished[code],
            location=loc["PFN-FRAIS-A"],
            quantity=Decimal(quantity),
            warehouse=warehouses[warehouse],
        )
    return {"fabrications": 4, "expéditions": len(shipments)}
