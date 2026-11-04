"""Deux enseignes, leurs entrepôts, des lasagnes Brévanne et MDD, et leurs tarifs."""

from datetime import datetime, time, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from referentiel.models import Article, CustomerWarehouse
from ventes.models import SalePrice


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
