"""EDI simulé : intégration, rejet, simulation quotidienne, API et droits."""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from ventes import edi
from ventes.models import CustomerOrder, EdiMessage
from ventes.tests.conftest import at


def payload(**changes):
    message = {
        "message_id": "ENS2-20261104-001",
        "sender": "ENS2",
        "order_reference": "MP-458812",
        "delivery_location": "ENS2-E01",
        "requested_delivery_date": (timezone.localdate() + timedelta(days=1)).isoformat(),
        "lines": [{"article": "PF-PAT-LASBOL-BRE-300", "quantity": 480}],
    }
    message.update(changes)
    return message


@pytest.fixture
def setup(warehouses, prices, finished_product):
    return None


def test_un_message_valide_cree_une_commande(setup):
    message = edi.integrate_message(payload(), received_at=at(9, 30))

    assert message.status == "integre"
    order = message.order
    assert order.source == "edi"
    assert order.customer_reference == "MP-458812"
    assert order.lines.get().quantity == 480


def test_article_inconnu_rejete(setup):
    message = edi.integrate_message(
        payload(lines=[{"article": "PF-XXX-INCONNU-BRE-300", "quantity": 12}]),
        received_at=at(9, 30),
    )
    assert message.status == "rejete"
    assert message.errors == ["Article inconnu : PF-XXX-INCONNU-BRE-300."]
    assert CustomerOrder.objects.count() == 0


def test_commande_apres_11_h_pour_le_lendemain_rejetee(setup):
    message = edi.integrate_message(payload(), received_at=at(11, 30))
    assert message.status == "rejete"
    assert "heure limite 11 h" in message.errors[0]


def test_champs_manquants(setup):
    message = edi.integrate_message({"message_id": "X", "sender": "ENS2"}, received_at=at(9))
    assert message.status == "rejete"
    assert "delivery_location" in message.errors[0]


def test_un_doublon_est_ignore(setup):
    edi.integrate_message(payload(), received_at=at(9, 30))
    duplicate = edi.integrate_message(payload(), received_at=at(9, 31))
    assert duplicate.status == "rejete"
    assert "doublon" in duplicate.errors[0]
    assert CustomerOrder.objects.count() == 1


def test_le_message_est_garde_tel_quel(setup):
    original = payload()
    message = edi.integrate_message(original, received_at=at(9, 30))
    assert EdiMessage.objects.get(pk=message.pk).payload == original


def test_simulation_d_une_journee(setup):
    messages = edi.simulate_day(at(9, 30), seed=42)
    # Une commande par enseigne ayant un assortiment tarifé
    assert {m.customer.code for m in messages} == {"ENS2", "ENS4"}
    for message in messages:
        if message.status == "integre":
            lines = message.order.lines.all()
            assert all(line.quantity % 12 == 0 for line in lines)  # par colis de 12


def test_la_simulation_glisse_parfois_une_erreur(setup, monkeypatch):
    monkeypatch.setattr(edi, "ERROR_RATE", 1.0)
    messages = edi.simulate_day(at(9, 30), seed=7)
    assert all(message.status == "rejete" for message in messages)


def test_la_simulation_est_planifiee_en_semaine_a_9_h_30():
    from django.conf import settings

    schedule = settings.CELERY_BEAT_SCHEDULE["simulation-edi-commandes"]["schedule"]
    assert schedule.hour == {9} and schedule.minute == {30}
    assert schedule.day_of_week == {1, 2, 3, 4, 5}


# --- API et droits --------------------------------------------------------------------


@pytest.mark.parametrize(("role", "expected"), [("commercial", 201), ("magasinier", 403)])
def test_seul_le_commercial_saisit_une_commande(
    api_client_for, private_label_customer, warehouses, finished_product, prices, role, expected
):
    response = api_client_for(role).post(
        "/api/ventes/orders/",
        {
            "customer": private_label_customer.id,
            "warehouse": warehouses["ENS2-E01"].id,
            "requested_delivery_date": str(timezone.localdate() + timedelta(days=2)),
            "lines": [{"article": finished_product.id, "quantity": "120"}],
        },
        format="json",
    )
    assert response.status_code == expected
    if expected == 201:
        assert response.json()["source"] == "manuel"
        assert response.json()["total_amount"] == "258.00"


def test_deposer_un_message_par_l_api(api_client_for, setup):
    body = (
        api_client_for("commercial")
        .post(
            "/api/ventes/edi-messages/receive/",
            payload(requested_delivery_date=(timezone.localdate() + timedelta(days=2)).isoformat()),
            format="json",
        )
        .json()
    )
    assert body["status"] == "integre"
    assert body["order"]["number"].startswith("CC-")


def test_simuler_par_l_api(api_client_for, setup):
    response = api_client_for("commercial").post("/api/ventes/edi-messages/simulate/")
    assert response.status_code == 201
    assert len(response.json()) == 2


def test_produits_commandables_par_l_api(api_client_for, private_label_customer, prices):
    body = (
        api_client_for("commercial")
        .get(f"/api/ventes/orderable-articles/?customer={private_label_customer.id}")
        .json()
    )
    assert {row["article_code"] for row in body["articles"]} == {
        "PF-PAT-LASBOL-BRE-300",
        "PF-PAT-LASBOL-ENS2-300",
    }
    assert body["earliest_delivery_date"]


def test_donnees_de_demo_des_ventes(db):
    call_command("charger_donnees_demo")
    assert EdiMessage.objects.filter(status="rejete").count() >= 1
    assert CustomerOrder.objects.filter(source="edi").exists()
    count = CustomerOrder.objects.count()
    call_command("charger_donnees_demo")
    assert CustomerOrder.objects.count() == count
