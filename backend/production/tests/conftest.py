"""Une usine, une ligne, une béchamel (crème + lait) et des lots libérés pour la fabriquer."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from referentiel.choices import ArticleType, TemperatureClass, Unit
from referentiel.models import (
    Article,
    BillOfMaterials,
    BOMLine,
    Location,
    ProductionLine,
    Site,
)
from stocks import services as stock_services


@pytest.fixture
def factory(factory_site):
    """Usine NAN avec sa chambre froide matières et sa chambre froide semi-finis."""
    rooms = {}
    for code in ("NAN-CF-MP", "NAN-CF-SF"):
        rooms[code] = Location.objects.create(
            site=factory_site, code=code, name=code, temperature_class=TemperatureClass.CHILLED
        )
    platform = Site.objects.create(code="PFN", name="Plateforme", site_type="plateforme")
    rooms["PFN-QUAR"] = Location.objects.create(
        site=platform, code="PFN-QUAR", name="Quarantaine",
        temperature_class=TemperatureClass.CHILLED,
    )  # fmt: skip
    return rooms


@pytest.fixture
def milk(dairy):
    return Article.objects.create(
        code="MP-LAI-LAIT", name="Lait", article_type=ArticleType.RAW_MATERIAL,
        unit=Unit.LITRE, category=dairy, shelf_life_days=10,
    )  # fmt: skip


@pytest.fixture
def bechamel(semi_finished, cream, milk):
    """Béchamel : pour 100 kg, 70 l de lait et 10 kg de crème (5 % de perte sur la crème)."""
    bom = BillOfMaterials.objects.create(article=semi_finished, base_quantity=Decimal("100"))
    BOMLine.objects.create(bom=bom, component=milk, quantity=Decimal("70"), unit="l")
    BOMLine.objects.create(
        bom=bom, component=cream, quantity=Decimal("10"), unit="kg", loss_rate=Decimal("5")
    )
    return semi_finished


@pytest.fixture
def stock_lot(factory):
    """Crée un lot libéré dans la chambre froide matières de l'usine."""

    def _make(article, quantity, expiry_in=20):
        today = timezone.localdate()
        lot = stock_services.receive_lot(
            article=article,
            supplier=None,
            quantity=Decimal(quantity),
            location=factory["NAN-CF-MP"],
            reception_date=today,
            expiry_date=today + timedelta(days=expiry_in),
            supplier_lot_number="F",
            block_reasons=[],
            user=None,
            reference="REC-T",
        )
        return stock_services.release_lot(lot)

    return _make


@pytest.fixture
def lasagna_line(factory_site, family, bechamel, finished_product):
    """Ligne L1 : famille PAT, 300 g, 2 400 unités / h. Lasagnes = 0,09 kg de béchamel."""
    line = ProductionLine.objects.create(
        code="L1", name="Pâtes 300 g", site=factory_site, formats=[300], capacity_per_hour=2400
    )
    line.families.add(family)
    bom = BillOfMaterials.objects.create(article=finished_product)
    BOMLine.objects.create(bom=bom, component=bechamel, quantity=Decimal("0.09"), unit="kg")
    return line
