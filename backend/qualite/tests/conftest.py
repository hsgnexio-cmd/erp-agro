"""Une petite chaîne complète pour tester la traçabilité.

Crème (lot A) + crème (lot B) → béchamel → lasagnes Brévanne → livrées à ENS2.
Les barquettes (emballage) entrent aussi dans les lasagnes.
"""

from decimal import Decimal

import pytest

from production.services import record_production
from referentiel.choices import ArticleType, SiteType, TemperatureClass, Unit
from referentiel.models import (
    Article,
    BillOfMaterials,
    BOMLine,
    CustomerWarehouse,
    Location,
    Site,
)
from stocks import services as stock_services
from ventes.services import record_shipment


@pytest.fixture
def chain(make_lot_for_trace, cream, semi_finished, finished_product, private_label_customer):
    site = Site.objects.create(code="MPE", name="Entrepôt", site_type=SiteType.WAREHOUSE)
    cold = Location.objects.create(
        site=site, code="MPE-FP-01", name="Froid", temperature_class=TemperatureClass.CHILLED
    )
    dry = Location.objects.create(
        site=site, code="MPE-AMB-01", name="Ambiant", temperature_class=TemperatureClass.AMBIENT
    )
    tray = Article.objects.create(
        code="EM-BARQ-300N", name="Barquette", article_type=ArticleType.PACKAGING, unit=Unit.UNIT
    )
    bechamel_bom = BillOfMaterials.objects.create(
        article=semi_finished, base_quantity=Decimal("100")
    )
    BOMLine.objects.create(bom=bechamel_bom, component=cream, quantity=Decimal("10"), unit="kg")
    lasagna_bom = BillOfMaterials.objects.create(article=finished_product)
    BOMLine.objects.create(
        bom=lasagna_bom, component=semi_finished, quantity=Decimal("0.09"), unit="kg"
    )
    BOMLine.objects.create(bom=lasagna_bom, component=tray, quantity=Decimal("1"), unit="u")

    cream_a = stock_services.release_lot(make_lot_for_trace(cream, "100", cold))
    cream_b = stock_services.release_lot(make_lot_for_trace(cream, "100", cold))
    trays = stock_services.release_lot(make_lot_for_trace(tray, "5000", dry, expiry_in=None))

    bechamel = record_production(
        article=semi_finished,
        quantity=Decimal("200"),
        location=cold,
        consumptions=[
            {"lot": cream_a, "location": cold, "quantity": Decimal("20")},
            {"lot": cream_b, "location": cold, "quantity": Decimal("5")},
        ],
    )
    bechamel = stock_services.release_lot(bechamel)
    lasagna = record_production(
        article=finished_product,
        quantity=Decimal("1000"),
        location=cold,
        consumptions=[
            {"lot": bechamel, "location": cold, "quantity": Decimal("90")},
            {"lot": trays, "location": dry, "quantity": Decimal("1000")},
        ],
    )
    lasagna = stock_services.release_lot(lasagna)
    warehouse = CustomerWarehouse.objects.create(
        customer=private_label_customer, code="ENS2-E01", name="Entrepôt Marché Plus", city="Nantes"
    )
    record_shipment(lot=lasagna, location=cold, quantity=Decimal("600"), warehouse=warehouse)
    return {
        "cream_a": cream_a,
        "cream_b": cream_b,
        "trays": trays,
        "bechamel": bechamel,
        "lasagna": lasagna,
        "cold": cold,
        "warehouse": warehouse,
    }


@pytest.fixture
def make_lot_for_trace(db):
    from datetime import timedelta

    from django.utils import timezone

    def _make(article, quantity, location, expiry_in=20):
        today = timezone.localdate()
        return stock_services.receive_lot(
            article=article,
            supplier=None,
            quantity=Decimal(quantity),
            location=location,
            reception_date=today,
            expiry_date=today + timedelta(days=expiry_in) if expiry_in else None,
            supplier_lot_number="F",
            block_reasons=[],
            user=None,
            reference="REC-T",
        )

    return _make
