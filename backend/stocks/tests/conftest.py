"""Données de test des stocks : un entrepôt, une usine, des emplacements et des lots."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from referentiel.choices import SiteType, TemperatureClass
from referentiel.models import Location, Site
from stocks.services import receive_lot


@pytest.fixture
def warehouse(db):
    return Site.objects.create(code="MPE", name="Entrepôt", site_type=SiteType.WAREHOUSE)


def make_location(site, code, temperature_class=TemperatureClass.CHILLED):
    return Location.objects.create(
        site=site, code=code, name=code, temperature_class=temperature_class
    )


@pytest.fixture
def quarantine(warehouse):
    return make_location(warehouse, "MPE-QUAR")


@pytest.fixture
def cold_room(warehouse):
    return make_location(warehouse, "MPE-FP-01")


@pytest.fixture
def ambient_store(warehouse):
    return make_location(warehouse, "MPE-AMB-01", TemperatureClass.AMBIENT)


@pytest.fixture
def factory_cold_room(factory_site):
    return make_location(factory_site, "NAN-CF-MP")


@pytest.fixture
def make_lot(quarantine):
    """Crée un lot reçu : make_lot(cream, "100", expiry_in=20, blocked=False)."""

    def _make(article, quantity="100", *, expiry_in=20, location=None, block_reasons=None):
        today = timezone.localdate()
        return receive_lot(
            article=article,
            supplier=None,
            quantity=Decimal(quantity),
            location=location or quarantine,
            reception_date=today,
            expiry_date=today + timedelta(days=expiry_in) if expiry_in is not None else None,
            supplier_lot_number="F-1",
            block_reasons=block_reasons or [],
            user=None,
            reference="REC-TEST",
        )

    return _make


@pytest.fixture
def expired_date():
    return timezone.localdate() - timedelta(days=1)


__all__ = ["date", "make_location"]
