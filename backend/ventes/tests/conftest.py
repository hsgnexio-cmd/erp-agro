"""Deux enseignes, leurs entrepôts, des lasagnes Brévanne et MDD, leurs tarifs, du stock à la
plateforme PFN et des commandes à préparer."""

from datetime import datetime, time, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from referentiel.choices import SiteType, TemperatureClass
from referentiel.models import Article, CustomerWarehouse, Location, Site
from stocks import services as stock_services
from ventes import orders
from ventes.models import SalePrice

TODAY = timezone.localdate


@pytest.fixture
def mdd_lasagna(recipe, private_label_customer):
    return Article.objects.create(
        name="Lasagnes MDD Marché Plus", article_type="PF", unit="u", recipe=recipe,
        brand_customer=private_label_customer, format_size=300, shelf_life_days=14,
    )  # fmt: skip


@pytest.fixture
def warehouses(private_label_customer, brand_only_customer):
    return {
        code: CustomerWarehouse.objects.create(
            customer=customer, code=code, name=f"Entrepôt {code}", city="Nantes"
        )
        for code, customer in (
            ("ENS2-E01", private_label_customer),
            ("ENS4-E01", brand_only_customer),
        )
    }


@pytest.fixture
def prices(finished_product, mdd_lasagna, private_label_customer, brand_only_customer):
    start = timezone.localdate() - timedelta(days=30)
    for customer, article, price in (
        (private_label_customer, finished_product, "2.15"),
        (private_label_customer, mdd_lasagna, "1.89"),
        (brand_only_customer, finished_product, "2.25"),
    ):
        SalePrice.objects.create(
            customer=customer, article=article, unit_price=Decimal(price), valid_from=start
        )


def at(hour: int, minute: int = 0, days: int = 0) -> datetime:
    """Date et heure du jour (ou d'un autre jour), dans le fuseau de Paris."""
    day = timezone.localdate() + timedelta(days=days)
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


# --- Préparation et expédition (partie 7b) -------------------------------------------


@pytest.fixture
def platform(db):
    site = Site.objects.create(code="PFN", name="Plateforme", site_type=SiteType.PLATFORM)
    return {
        code: Location.objects.create(
            site=site, code=code, name=code, temperature_class=TemperatureClass.CHILLED
        )
        for code in ("PFN-FRAIS-A", "PFN-FRAIS-B")
    }


@pytest.fixture
def make_pf_lot(platform):
    """Lot de produit fini libéré à la plateforme, périmant dans `expiry_in` jours."""

    def _make(article, quantity, expiry_in, location="PFN-FRAIS-A"):
        lot = stock_services.receive_lot(
            article=article,
            supplier=None,
            quantity=Decimal(quantity),
            location=platform[location],
            reception_date=TODAY(),
            expiry_date=TODAY() + timedelta(days=expiry_in),
            supplier_lot_number="",
            block_reasons=[],
            user=None,
            reference="TEST",
        )
        return stock_services.release_lot(lot)

    return _make


@pytest.fixture
def make_order(private_label_customer, warehouses, prices):
    """Commande de Marché Plus (ENS2, DLC minimale 70 %), livrable dans `days` jours."""

    def _make(lines, days=2):
        return orders.create_order(
            customer=private_label_customer,
            warehouse=warehouses["ENS2-E01"],
            requested_delivery_date=TODAY() + timedelta(days=days),
            lines=[{"article": article, "quantity": Decimal(q)} for article, q in lines],
            received_at=at(9, 0),
        )

    return _make


@pytest.fixture
def stock(make_pf_lot, finished_product):
    """Livraison à J+2, lasagnes 14 jours, 70 % → DLC minimale J+12.

    - court : DLC J+11, trop court pour l'enseigne ;
    - premier : DLC J+12, le premier à proposer (FEFO) ;
    - second : DLC J+13.
    """
    return {
        "court": make_pf_lot(finished_product, "500", 11),
        "premier": make_pf_lot(finished_product, "300", 12),
        "second": make_pf_lot(finished_product, "1000", 13, "PFN-FRAIS-B"),
    }
