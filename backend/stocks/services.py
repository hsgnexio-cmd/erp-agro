"""Logique métier des stocks : création des lots et des mouvements."""

from datetime import date
from decimal import Decimal

from django.db import transaction

from referentiel.models import Article, Location, Supplier
from referentiel.services import next_document_number

from .choices import LotStatus, MovementType
from .models import Lot, StockMovement


def next_received_lot_number(reception_date: date) -> str:
    """Numéro interne d'un lot reçu : LR-AAMMJJ-NNNN (LR = lot de réception)."""
    return next_document_number(f"LR-{reception_date:%y%m%d}", 4)


@transaction.atomic
def receive_lot(
    *,
    article: Article,
    supplier: Supplier,
    quantity: Decimal,
    location: Location,
    reception_date: date,
    expiry_date: date | None,
    supplier_lot_number: str,
    block_reasons: list[str],
    user,
    reference: str,
) -> Lot:
    """Crée un lot reçu et son mouvement d'entrée.

    Règle 6 : un lot reçu démarre en quarantaine, ou bloqué si un contrôle a échoué.
    """
    lot = Lot.objects.create(
        number=next_received_lot_number(reception_date),
        article=article,
        supplier=supplier,
        supplier_lot_number=supplier_lot_number,
        reception_date=reception_date,
        date_type=article.date_type,
        expiry_date=expiry_date,
        initial_quantity=quantity,
        location=location,
        status=LotStatus.BLOCKED if block_reasons else LotStatus.QUARANTINE,
        block_reason=" ; ".join(block_reasons),
    )
    StockMovement.objects.create(
        lot=lot,
        movement_type=MovementType.RECEPTION,
        quantity=quantity,
        location=location,
        user=user if user and user.is_authenticated else None,
        reason="Réception fournisseur",
        reference=reference,
    )
    return lot
