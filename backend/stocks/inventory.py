"""Inventaires : photo du stock, comptage à l'aveugle, ajustements à la validation.

Pendant un inventaire, les emplacements comptés sont gelés : aucun mouvement n'est
accepté (voir StockMovement.save), sauf les ajustements d'inventaire eux-mêmes.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from referentiel.models import Location, Site
from referentiel.services import next_document_number

from . import services
from .choices import InventoryStatus, LotStatus, MovementType
from .models import Inventory, InventoryLine, Lot, StockMovement


def _user(user):
    return user if user is not None and user.is_authenticated else None


def _check_open(inventory: Inventory) -> None:
    if inventory.status != InventoryStatus.OPEN:
        raise ValidationError(
            f"L'inventaire {inventory.number} est {inventory.get_status_display().lower()}."
        )


@transaction.atomic
def open_inventory(
    site: Site, *, location: Location | None = None, user=None, comment: str = ""
) -> Inventory:
    """Ouvre un inventaire et photographie le stock théorique du périmètre."""
    if location is not None and location.site_id != site.pk:
        raise ValidationError({"location": f"L'emplacement doit appartenir au site {site.code}."})
    overlap = Inventory.objects.filter(status=InventoryStatus.OPEN, site=site)
    if location is not None:
        overlap = overlap.filter(Q(location__isnull=True) | Q(location=location))
    existing = overlap.first()
    if existing:
        raise ValidationError(
            f"Un inventaire est déjà en cours sur ce périmètre ({existing.number})."
        )

    inventory = Inventory.objects.create(
        number=next_document_number(f"INV-{timezone.localdate().year}", 5),
        site=site,
        location=location,
        opened_by=_user(user),
        comment=comment.strip(),
    )
    movements = StockMovement.objects.filter(location__site=site).exclude(
        lot__status=LotStatus.DESTROYED
    )
    if location is not None:
        movements = movements.filter(location=location)
    rows = movements.values("lot", "location").annotate(total=Sum("quantity")).filter(total__gt=0)
    InventoryLine.objects.bulk_create(
        InventoryLine(
            inventory=inventory,
            lot_id=row["lot"],
            location_id=row["location"],
            expected_quantity=row["total"],
        )
        for row in rows
    )
    return inventory


def add_found_lot(
    inventory: Inventory, *, lot: Lot, location: Location, counted_quantity: Decimal
) -> InventoryLine:
    """Ajoute un lot trouvé sur place alors que le système ne le situait pas à cet endroit."""
    _check_open(inventory)
    if not inventory.covers(location):
        raise ValidationError({"location": "Cet emplacement n'est pas dans le périmètre compté."})
    if lot.status == LotStatus.DESTROYED:
        raise ValidationError({"lot": f"Le lot {lot.number} est détruit."})
    if inventory.lines.filter(lot=lot, location=location).exists():
        raise ValidationError({"lot": "Ce lot est déjà sur la feuille de comptage."})
    services.check_location_compatible(lot.article, location)
    if counted_quantity < 0:
        raise ValidationError(
            {"counted_quantity": "La quantité comptée ne peut pas être négative."}
        )
    return InventoryLine.objects.create(
        inventory=inventory,
        lot=lot,
        location=location,
        expected_quantity=services.quantity_at(lot, location),
        counted_quantity=counted_quantity,
        added_during_count=True,
    )


@transaction.atomic
def record_counts(inventory: Inventory, counts: dict[int, Decimal | None]) -> None:
    """Enregistre les quantités comptées : {id de ligne: quantité ou None pour effacer}."""
    _check_open(inventory)
    lines = {line.id: line for line in inventory.lines.all()}
    for line_id, quantity in counts.items():
        line = lines.get(line_id)
        if line is None:
            raise ValidationError(f"La ligne {line_id} n'appartient pas à cet inventaire.")
        if quantity is not None and quantity < 0:
            raise ValidationError(
                {"counted_quantity": "La quantité comptée ne peut pas être négative."}
            )
        line.counted_quantity = quantity
        line.save(update_fields=["counted_quantity"])


@transaction.atomic
def validate_inventory(inventory: Inventory, *, user=None) -> list[StockMovement]:
    """Valide l'inventaire : chaque écart devient un mouvement d'ajustement (règle 11)."""
    inventory = Inventory.objects.select_for_update().get(pk=inventory.pk)
    _check_open(inventory)
    missing = inventory.lines.filter(counted_quantity__isnull=True).count()
    if missing:
        raise ValidationError(f"{missing} ligne(s) n'ont pas encore été comptées.")

    adjustments = []
    for line in inventory.lines.select_related("lot", "location"):
        difference = line.counted_quantity - services.quantity_at(line.lot, line.location)
        if difference != 0:
            adjustments.append(
                StockMovement.objects.create(
                    lot=line.lot,
                    movement_type=MovementType.INVENTORY,
                    quantity=difference,
                    location=line.location,
                    user=_user(user),
                    reason=f"Écart d'inventaire {inventory.number}",
                    reference=inventory.number,
                )
            )
    inventory.status = InventoryStatus.VALIDATED
    inventory.closed_at = timezone.now()
    inventory.closed_by = _user(user)
    inventory.save()
    return adjustments


def cancel_inventory(inventory: Inventory, *, user=None) -> Inventory:
    """Annule l'inventaire sans rien ajuster ; les emplacements sont dégelés."""
    _check_open(inventory)
    inventory.status = InventoryStatus.CANCELLED
    inventory.closed_at = timezone.now()
    inventory.closed_by = _user(user)
    inventory.save()
    return inventory
