"""Inventaires : photo du stock, gel des emplacements, ajustements à la validation."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from stocks import inventory, services
from stocks.choices import InventoryStatus, MovementType


@pytest.fixture
def stocked(make_lot, cream, cold_room):
    """Deux lots de crème : 100 kg en quarantaine, 60 kg en chambre froide."""
    first = make_lot(cream, "100")
    second = services.release_lot(make_lot(cream, "60"))
    services.transfer(
        second, from_location=second.location, to_location=cold_room, quantity=Decimal("60")
    )
    return first, second


def test_ouverture_photographie_le_stock(stocked, warehouse, make_user):
    inv = inventory.open_inventory(warehouse, user=make_user("magasinier"))

    assert inv.number.startswith("INV-")
    lines = {(line.lot_id, line.location.code): line.expected_quantity for line in inv.lines.all()}
    assert lines == {
        (stocked[0].id, "MPE-QUAR"): Decimal("100"),
        (stocked[1].id, "MPE-FP-01"): Decimal("60"),
    }


def test_inventaire_d_un_seul_emplacement(stocked, warehouse, cold_room):
    inv = inventory.open_inventory(warehouse, location=cold_room)
    assert [line.lot for line in inv.lines.all()] == [stocked[1]]


def test_les_emplacements_comptes_sont_geles(stocked, warehouse, cold_room, quarantine):
    inv = inventory.open_inventory(warehouse, location=cold_room)
    with pytest.raises(ValidationError) as exc:
        services.transfer(
            stocked[0], from_location=quarantine, to_location=cold_room, quantity=Decimal("1")
        )
    assert inv.number in exc.value.messages[0]

    # Un emplacement hors du périmètre reste libre
    services.correct_movement(
        stocked[0].movements.get(movement_type="reception"),
        quantity=Decimal("1"),
        reason="Erreur de pesée",
    )
    inventory.cancel_inventory(inv)
    services.transfer(
        stocked[0], from_location=quarantine, to_location=cold_room, quantity=Decimal("1")
    )


def test_deux_inventaires_ne_se_chevauchent_pas(stocked, warehouse, cold_room):
    inventory.open_inventory(warehouse, location=cold_room)
    with pytest.raises(ValidationError):
        inventory.open_inventory(warehouse)


def test_validation_cree_les_ajustements(stocked, warehouse, make_user):
    inv = inventory.open_inventory(warehouse)
    lines = {line.location.code: line for line in inv.lines.all()}
    inventory.record_counts(
        inv,
        {lines["MPE-QUAR"].id: Decimal("100"), lines["MPE-FP-01"].id: Decimal("57.5")},
    )
    adjustments = inventory.validate_inventory(inv, user=make_user("magasinier"))

    assert len(adjustments) == 1
    adjustment = adjustments[0]
    assert adjustment.movement_type == MovementType.INVENTORY
    assert adjustment.quantity == Decimal("-2.5")
    assert adjustment.reference == inv.number
    assert stocked[1].quantity == Decimal("57.5")
    inv.refresh_from_db()
    assert inv.status == InventoryStatus.VALIDATED


def test_toutes_les_lignes_doivent_etre_comptees(stocked, warehouse):
    inv = inventory.open_inventory(warehouse)
    with pytest.raises(ValidationError) as exc:
        inventory.validate_inventory(inv)
    assert "2 ligne(s)" in exc.value.messages[0]


def test_quantite_negative_refusee(stocked, warehouse):
    inv = inventory.open_inventory(warehouse)
    with pytest.raises(ValidationError):
        inventory.record_counts(inv, {inv.lines.first().id: Decimal("-1")})


def test_lot_trouve_pendant_le_comptage(stocked, warehouse, cold_room):
    inv = inventory.open_inventory(warehouse, location=cold_room)
    line = inventory.add_found_lot(
        inv, lot=stocked[0], location=cold_room, counted_quantity=Decimal("5")
    )
    assert line.expected_quantity == 0
    inventory.record_counts(inv, {inv.lines.get(lot=stocked[1]).id: Decimal("60")})
    inventory.validate_inventory(inv)

    stock = {loc.code: qty for loc, qty in services.stock_by_location(stocked[0])}
    assert stock["MPE-FP-01"] == Decimal("5")


def test_inventaire_clos_non_modifiable(stocked, warehouse):
    inv = inventory.cancel_inventory(inventory.open_inventory(warehouse))
    with pytest.raises(ValidationError):
        inventory.record_counts(inv, {inv.lines.first().id: Decimal("1")})
