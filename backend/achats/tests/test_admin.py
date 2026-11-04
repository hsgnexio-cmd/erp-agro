"""Les écrans d'administration des achats et des stocks s'ouvrent sans erreur."""

import pytest
from django.core.management import call_command
from django.urls import reverse

from achats.models import PurchaseOrder, Reception
from stocks.models import Lot


@pytest.fixture
def admin_client_with_data(admin_client):
    call_command("charger_donnees_demo")
    return admin_client


def test_les_ecrans_s_affichent(admin_client_with_data):
    client = admin_client_with_data
    urls = [
        reverse("admin:achats_supplierprice_changelist"),
        reverse("admin:achats_purchaseorder_changelist"),
        reverse("admin:achats_reception_changelist"),
        reverse("admin:stocks_lot_changelist"),
        reverse("admin:stocks_stockmovement_changelist"),
        reverse("admin:achats_purchaseorder_change", args=[PurchaseOrder.objects.first().id]),
        reverse("admin:achats_reception_change", args=[Reception.objects.first().id]),
        reverse("admin:stocks_lot_change", args=[Lot.objects.first().id]),
    ]
    for url in urls:
        assert client.get(url).status_code == 200, url


def test_les_donnees_de_demo_des_achats(admin_client_with_data):
    assert PurchaseOrder.objects.count() == 10
    assert Lot.objects.filter(status="bloque").count() == 2
    # Plusieurs lots de crème pour le futur scénario de rappel produit (phase 5)
    assert Lot.objects.filter(article__code="MP-LAI-CREME35").count() == 2
