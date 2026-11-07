"""Deux enseignes (ENS2 avec MDD, ENS4 marque seule), lasagnes Brévanne et MDD ENS2, et un
outil pour passer des commandes livrées n'importe quelle semaine."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from previsions.forecast import current_week
from referentiel.models import Article, CustomerWarehouse
from ventes import orders


def week(offset: int) -> date:
    """Lundi de la semaine courante + `offset` semaines (S-1 = -1, S+1 = 1)."""
    return current_week() + timedelta(days=7 * offset)


def moment(day: date, hour: int = 5) -> datetime:
    return timezone.make_aware(datetime.combine(day, time(hour, 0)))


@pytest.fixture
def mdd_lasagna(recipe, private_label_customer):
    return Article.objects.create(
        name="Lasagnes MDD Marché Plus", article_type="PF", unit="u", recipe=recipe,
        brand_customer=private_label_customer, format_size=300, shelf_life_days=14,
    )  # fmt: skip


@pytest.fixture
def warehouses(private_label_customer, brand_only_customer):
    return {
        customer.code: CustomerWarehouse.objects.create(
            customer=customer, code=f"{customer.code}-E01", name="Entrepôt", city="Nantes"
        )
        for customer in (private_label_customer, brand_only_customer)
    }


@pytest.fixture
def place_order(warehouses):
    """Commande d'une enseigne, livrée le jour `delivery` (reçue l'avant-veille à 9 h)."""

    def _place(customer, article, quantity, delivery: date):
        return orders.create_order(
            customer=customer,
            warehouse=warehouses[customer.code],
            requested_delivery_date=delivery,
            lines=[{"article": article, "quantity": Decimal(quantity)}],
            received_at=moment(delivery - timedelta(days=2), 9),
        )

    return _place
