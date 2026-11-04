"""Données de démonstration des stocks : libérations, transferts, destruction.

S'appuie sur les lots créés par les réceptions de démonstration (achats/demo_data.py).
"""

from decimal import Decimal

from django.db import transaction

from referentiel.models import Location

from . import services
from .models import Lot, LotStatusChange

# Lots conformes libérés par la qualité, puis rangés : (lot fournisseur, emplacement de stockage)
RELEASED_AND_STORED = [
    ("CB-0412", "MPE-FP-01"),  # crème
    ("CB-E-118", "MPE-FP-01"),  # emmental
    ("SA-PP-2291", "MPE-FN-01"),  # petits pois surgelés
    ("CB-0419", "MPE-FP-01"),  # crème
    ("CB-P-077", "MPE-FP-01"),  # parmesan
    ("VO-26-3322", "MPE-FP-01"),  # veau
]
# Approvisionnement de l'usine de Nantes : (lot fournisseur, quantité)
SENT_TO_FACTORY = [("CB-0412", "150"), ("VO-26-3322", "100")]
QUALITY_REASON = "Contrôle qualité à réception conforme"


@transaction.atomic
def load_demo_data() -> dict[str, int | str]:
    if LotStatusChange.objects.exists():
        return {"mouvements de stock": "déjà présents, non modifiés"}

    lots = {lot.supplier_lot_number: lot for lot in Lot.objects.all()}
    locations = {location.code: location for location in Location.objects.all()}
    released = transfers = 0

    for supplier_lot, storage in RELEASED_AND_STORED:
        lot = lots.get(supplier_lot)
        if lot is None or lot.status != "quarantaine":
            continue
        services.release_lot(lot, reason=QUALITY_REASON)
        released += 1
        for location, quantity in services.stock_by_location(lot):
            if location.code != storage:
                services.transfer(
                    lot,
                    from_location=location,
                    to_location=locations[storage],
                    quantity=quantity,
                    reason="Rangement après libération",
                )
                transfers += 1

    for supplier_lot, quantity in SENT_TO_FACTORY:
        lot = lots.get(supplier_lot)
        if lot is None:
            continue
        services.transfer(
            lot,
            from_location=locations["MPE-FP-01"],
            to_location=locations["NAN-CF-MP"],
            quantity=Decimal(quantity),
            reason="Approvisionnement usine NAN",
        )
        transfers += 1

    destroyed = 0
    beef = lots.get("VO-26-3321")  # bœuf reçu à 6,5 °C
    if beef is not None and beef.status == "bloque":
        services.destroy_lot(
            beef, reason="Rupture de la chaîne du froid confirmée par la qualité : destruction"
        )
        destroyed = 1

    return {"lots libérés": released, "transferts": transfers, "lots détruits": destroyed}
