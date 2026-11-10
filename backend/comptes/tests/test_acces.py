"""Matrice d'accès en lecture (moindre privilège) : domaines par rôle et prix masqués."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from achats import services as purchasing
from comptes.access import READ_AREAS, readable_areas
from referentiel.models import CustomerWarehouse, Site, Supplier
from ventes import orders as sales


def test_chaque_role_voit_son_metier_et_le_socle_commun(make_user):
    commun = {"referentiel", "stocks", "qualite"}
    attendu = {
        "direction": set(READ_AREAS),
        "acheteur": commun | {"achats", "prix_achat", "mrp", "production", "previsions"},
        "magasinier": commun | {"achats", "ventes"},
        "production": commun | {"achats", "mrp", "production", "previsions"},
        "qualite": commun | {"achats", "production", "ventes"},
        "commercial": commun | {"ventes", "prix_vente", "previsions"},
    }
    for role, areas in attendu.items():
        assert set(readable_areas(make_user(role))) == areas, role


@pytest.mark.parametrize(
    ("role", "url", "status"),
    [
        ("commercial", "/api/production/orders/", 403),
        ("magasinier", "/api/previsions/forecast/", 403),
        ("production", "/api/ventes/orders/", 403),
        ("magasinier", "/api/ventes/prices/", 403),
        ("acheteur", "/api/achats/prices/", 200),
        ("commercial", "/api/stocks/lots/", 200),  # stocks : tout le monde
        ("qualite", "/api/qualite/recalls/", 200),
    ],
)
def test_le_serveur_refuse_les_donnees_hors_du_role(api_client_for, role, url, status):
    response = api_client_for(role).get(url)
    assert response.status_code == status
    if status == 403:
        assert response.json()["detail"] == "Ton rôle ne donne pas accès à ces données."


def test_le_me_renvoie_les_domaines_pour_le_menu(api_client_for):
    me = api_client_for("commercial").get("/api/auth/me/").json()
    assert "prix_vente" in me["areas"] and "production" not in me["areas"]


def test_prix_d_achat_masques_pour_le_quai(api_client_for, cream, factory_site):
    from achats.tests.conftest import reference

    site = Site.objects.create(code="MPE", name="Entrepôt", site_type="entrepot")
    supplier = Supplier.objects.create(
        code="FOU-004", name="Crèmerie", lead_time_days=3, audited=True,
        last_audit_date=timezone.localdate(),
    )  # fmt: skip
    reference(supplier, cream, price="4.20")
    order = purchasing.create_purchase_order(
        supplier=supplier, delivery_site=site, lines=[{"article": cream, "quantity": Decimal("10")}]
    )
    url = f"/api/achats/orders/{order.pk}/"
    buyer = api_client_for("acheteur").get(url).json()
    assert buyer["total_amount"] == "42.00" and buyer["lines"][0]["unit_price"] == "4.2000"
    quay = api_client_for("magasinier").get(url).json()
    assert quay["total_amount"] is None
    assert quay["lines"][0]["unit_price"] is None and quay["lines"][0]["amount"] is None
    assert quay["lines"][0]["quantity"] == "10.000"  # la commande reste lisible


def test_prix_de_vente_masques_pour_le_quai(
    api_client_for, private_label_customer, finished_product
):
    warehouse = CustomerWarehouse.objects.create(
        customer=private_label_customer, code="ENS2-E01", name="Entrepôt", city="Nantes"
    )
    from ventes.models import SalePrice

    SalePrice.objects.create(
        customer=private_label_customer, article=finished_product, unit_price=Decimal("2.15"),
        valid_from=timezone.localdate() - timedelta(days=10),
    )  # fmt: skip
    order = sales.create_order(
        customer=private_label_customer, warehouse=warehouse,
        requested_delivery_date=timezone.localdate() + timedelta(days=2),
        lines=[{"article": finished_product, "quantity": Decimal("120")}],
    )  # fmt: skip
    url = f"/api/ventes/orders/{order.pk}/"
    assert api_client_for("commercial").get(url).json()["total_amount"] == "258.00"
    quay = api_client_for("magasinier").get(url).json()
    assert quay["total_amount"] is None and quay["lines"][0]["unit_price"] is None
    listing = api_client_for("qualite").get("/api/ventes/orders/").json()
    assert listing["results"][0]["total_amount"] is None
