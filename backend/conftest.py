"""Outils partagés par tous les tests (« fixtures » pytest)."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from referentiel.choices import ArticleType, DateType, SiteType, TemperatureClass, Unit
from referentiel.models import (
    Article,
    Customer,
    MaterialCategory,
    ProductFamily,
    Recipe,
    Site,
)


@pytest.fixture
def make_user(db):
    """Crée un utilisateur avec un rôle : make_user("qualite")."""

    def _make(role: str | None = None, username: str | None = None):
        user = get_user_model().objects.create_user(
            username=username or f"user-{role or 'sans-role'}", password="motdepasse-test"
        )
        if role:
            user.groups.add(Group.objects.get(name=role))
        return user

    return _make


@pytest.fixture
def api_client_for(make_user):
    """Client API connecté avec un rôle donné : api_client_for("acheteur")."""

    def _client(role: str | None = None):
        client = APIClient()
        client.force_authenticate(make_user(role))
        return client

    return _client


@pytest.fixture
def factory_site(db):
    return Site.objects.create(code="NAN", name="Usine plats chauds", site_type=SiteType.FACTORY)


@pytest.fixture
def family(factory_site):
    return ProductFamily.objects.create(code="PAT", name="Plats à base de pâtes", site=factory_site)


@pytest.fixture
def recipe(family):
    return Recipe.objects.create(code="LASBOL", name="Lasagnes bolognaise", family=family)


@pytest.fixture
def dairy(db):
    return MaterialCategory.objects.create(
        code="LAI",
        name="Produits laitiers",
        temperature_class=TemperatureClass.CHILLED,
        date_type=DateType.DLC,
    )


@pytest.fixture
def dry(db):
    return MaterialCategory.objects.create(
        code="SEC",
        name="Produits secs",
        temperature_class=TemperatureClass.AMBIENT,
        date_type=DateType.DDM,
    )


@pytest.fixture
def private_label_customer(db):
    return Customer.objects.create(
        code="ENS2",
        name="Marché Plus",
        customer_type="hyper_super",
        sells_brand=True,
        sells_private_label=True,
        min_remaining_shelf_life_pct=Decimal("70"),
    )


@pytest.fixture
def brand_only_customer(db):
    return Customer.objects.create(
        code="ENS4",
        name="Proxi Ville",
        customer_type="proximite",
        sells_brand=True,
        sells_private_label=False,
        min_remaining_shelf_life_pct=Decimal("75"),
    )


@pytest.fixture
def cream(dairy):
    return Article.objects.create(
        code="MP-LAI-CREME35",
        name="Crème 35 %",
        article_type=ArticleType.RAW_MATERIAL,
        unit=Unit.KG,
        category=dairy,
        shelf_life_days=21,
    )


@pytest.fixture
def flour(dry):
    return Article.objects.create(
        code="MP-SEC-FARINE",
        name="Farine",
        article_type=ArticleType.RAW_MATERIAL,
        unit=Unit.KG,
        category=dry,
        shelf_life_days=365,
    )


@pytest.fixture
def semi_finished(db):
    return Article.objects.create(
        code="SF-BECHAMEL",
        name="Béchamel",
        article_type=ArticleType.SEMI_FINISHED,
        unit=Unit.KG,
        shelf_life_days=3,
    )


@pytest.fixture
def finished_product(recipe):
    return Article.objects.create(
        name="Lasagnes 300 g",
        article_type=ArticleType.FINISHED_PRODUCT,
        unit=Unit.UNIT,
        recipe=recipe,
        format_size=300,
        shelf_life_days=14,
    )
