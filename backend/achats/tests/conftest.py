"""Données de test des achats : entrepôt, fournisseur audité, articles référencés et tarifs."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from achats import services
from achats.models import SupplierPrice
from referentiel.choices import ArticleType, DateType, SiteType, TemperatureClass, Unit
from referentiel.models import Article, Location, MaterialCategory, Site, Supplier, SupplierArticle


@pytest.fixture
def warehouse(db):
    return Site.objects.create(code="MPE", name="Entrepôt", site_type=SiteType.WAREHOUSE)


@pytest.fixture
def quarantine(warehouse):
    return Location.objects.create(
        site=warehouse,
        code="MPE-QUAR",
        name="Quarantaine",
        temperature_class=TemperatureClass.CHILLED,
    )


@pytest.fixture
def quarantine_zones(warehouse, quarantine):
    """Une zone de quarantaine par classe de température."""
    zones = {TemperatureClass.CHILLED: quarantine}
    for temperature_class, code in (
        (TemperatureClass.FROZEN, "MPE-QUAR-FN"),
        (TemperatureClass.AMBIENT, "MPE-QUAR-AMB"),
    ):
        zones[temperature_class] = Location.objects.create(
            site=warehouse, code=code, name="Quarantaine", temperature_class=temperature_class
        )
    return zones


@pytest.fixture
def supplier(db):
    return Supplier.objects.create(
        code="FOU-004",
        name="Crèmerie Bretonne",
        lead_time_days=3,
        audited=True,
        last_audit_date=date(2026, 3, 15),
    )


def reference(supplier, article, price="4.20", minimum=None):
    link = SupplierArticle.objects.create(
        supplier=supplier, article=article, is_main_supplier=True, min_order_quantity=minimum
    )
    SupplierPrice.objects.create(
        supplier_article=link,
        unit_price=Decimal(price),
        valid_from=timezone.localdate() - timedelta(days=100),
    )
    return link


@pytest.fixture
def cream_at_supplier(supplier, cream):
    """Crème (DLC 21 jours, froid positif, seuil 60 % à réception) référencée à 4,20 €/kg."""
    cream.category.min_remaining_shelf_life_pct = Decimal("60")
    cream.category.save()
    return reference(supplier, cream)


@pytest.fixture
def flour_at_supplier(supplier, flour):
    return reference(supplier, flour, price="0.62")


@pytest.fixture
def peas(db):
    frozen = MaterialCategory.objects.create(
        code="SUR",
        name="Surgelés",
        temperature_class=TemperatureClass.FROZEN,
        date_type=DateType.DDM,
    )
    return Article.objects.create(
        code="MP-SUR-PETPOIS",
        name="Petits pois",
        article_type=ArticleType.RAW_MATERIAL,
        unit=Unit.KG,
        category=frozen,
        shelf_life_days=540,
    )


@pytest.fixture
def tray(db):
    return Article.objects.create(
        code="EM-BARQ-300N", name="Barquette", article_type=ArticleType.PACKAGING, unit=Unit.UNIT
    )


@pytest.fixture
def make_order(warehouse, supplier):
    def _make(*lines, send=True, **fields):
        order = services.create_purchase_order(
            supplier=fields.pop("supplier", supplier),
            delivery_site=warehouse,
            lines=[{"article": article, "quantity": Decimal(qty)} for article, qty in lines],
            **fields,
        )
        if send:
            services.send_order(order)
        return order

    return _make


@pytest.fixture
def receive(quarantine_zones):
    """Réceptionne une ligne de commande : receive(order, quantity="100", temperature="3")."""

    def _receive(order, *, article_code=None, documents_ok=True, **line):
        order_line = (
            order.lines.get(article__code=article_code) if article_code else order.lines.first()
        )
        today = timezone.localdate()
        data = {
            "order_line": order_line,
            "quantity": Decimal(line.pop("quantity", str(order_line.quantity))),
            "supplier_lot_number": line.pop("supplier_lot_number", "LOT-F-001"),
            "expiry_date": line.pop("expiry_date", today + timedelta(days=20)),
            "temperature": line.pop("temperature", Decimal("3")),
            "appearance_ok": line.pop("appearance_ok", True),
        }
        location = line.pop("location", None)
        data.update(line)
        if data["temperature"] is not None:
            data["temperature"] = Decimal(data["temperature"])
        return services.create_reception(
            order=order,
            location=location or quarantine_zones[order_line.article.storage_temperature_class],
            delivery_note_number="BL-001",
            documents_ok=documents_ok,
            lines=[data],
        )

    return _receive
