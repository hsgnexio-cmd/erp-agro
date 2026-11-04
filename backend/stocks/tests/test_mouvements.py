"""Règle 11 : un mouvement de stock ne se modifie ni ne se supprime jamais."""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from referentiel.choices import SiteType, TemperatureClass
from referentiel.models import Location, Site
from stocks.choices import LotStatus, MovementType
from stocks.models import Lot, StockMovement
from stocks.services import receive_lot


@pytest.fixture
def location(db):
    site = Site.objects.create(code="MPE", name="Entrepôt", site_type=SiteType.WAREHOUSE)
    return Location.objects.create(
        site=site, code="MPE-FP-01", name="Froid", temperature_class=TemperatureClass.CHILLED
    )


@pytest.fixture
def lot(cream, location):
    return receive_lot(
        article=cream,
        supplier=None,
        quantity=Decimal("100"),
        location=location,
        reception_date=date(2026, 11, 4),
        expiry_date=date(2026, 11, 24),
        supplier_lot_number="CB-1",
        block_reasons=[],
        user=None,
        reference="REC-TEST",
    )


def test_numero_de_lot(lot):
    assert lot.number == "LR-261104-0001"
    assert lot.status == LotStatus.QUARANTINE


def test_la_quantite_est_la_somme_des_mouvements(lot, location):
    StockMovement.objects.create(
        lot=lot,
        movement_type=MovementType.RECEPTION,
        quantity=Decimal("-30"),
        location=location,
        reason="Correction (mouvement inverse)",
    )
    assert lot.quantity == Decimal("70")


def test_un_mouvement_ne_se_modifie_pas(lot):
    movement = lot.movements.get()
    movement.quantity = Decimal("999")
    with pytest.raises(ValidationError):
        movement.save()


def test_un_mouvement_ne_se_supprime_pas(lot):
    with pytest.raises(ValidationError):
        lot.movements.get().delete()
    with pytest.raises(ValidationError):
        StockMovement.objects.all().delete()
    with pytest.raises(ValidationError):
        StockMovement.objects.all().update(quantity=0)
    assert StockMovement.objects.count() == 1


def test_un_lot_bloque_a_un_motif(cream, location):
    with pytest.raises(ValidationError):
        Lot.objects.create(
            number="LR-X",
            article=cream,
            date_type="DLC",
            expiry_date=date(2026, 11, 24),
            initial_quantity=Decimal("1"),
            location=location,
            status=LotStatus.BLOCKED,
        )


def test_la_dlc_est_obligatoire_pour_un_produit_frais(cream, location):
    with pytest.raises(ValidationError):
        Lot.objects.create(
            number="LR-X",
            article=cream,
            date_type="DLC",
            initial_quantity=Decimal("1"),
            location=location,
            status=LotStatus.QUARANTINE,
        )
