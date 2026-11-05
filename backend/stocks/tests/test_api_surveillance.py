"""API de la surveillance et droits par rôle."""

from decimal import Decimal

import pytest
from django.core.management import call_command

from stocks import services
from stocks.models import Alert, Inventory


@pytest.mark.parametrize(
    ("role", "expected"), [("magasinier", 201), ("qualite", 201), ("commercial", 403)]
)
def test_qui_peut_saisir_un_releve(api_client_for, quarantine, role, expected):
    response = api_client_for(role).post(
        "/api/stocks/temperatures/",
        {"location": quarantine.id, "temperature": "3.0"},
        format="json",
    )
    assert response.status_code == expected


def test_un_ecart_par_l_api_indique_les_lots_bloques(api_client_for, make_lot, cream, quarantine):
    lot = services.release_lot(make_lot(cream))
    body = (
        api_client_for("magasinier")
        .post(
            "/api/stocks/temperatures/",
            {"location": quarantine.id, "temperature": "6.5"},
            format="json",
        )
        .json()
    )
    assert body["is_compliant"] is False
    assert body["blocked_lots"] == [lot.number]
    assert "Écart de température" in body["alert"]


def test_derniers_releves(api_client_for, quarantine):
    client = api_client_for("qualite")
    client.post(
        "/api/stocks/temperatures/",
        {"location": quarantine.id, "temperature": "2.5"},
        format="json",
    )
    rows = client.get("/api/stocks/temperatures/latest/").json()
    assert rows[0]["location_code"] == "MPE-QUAR"
    assert rows[0]["last_reading"]["temperature"] == "2.5"


def test_comptage_a_l_aveugle(api_client_for, make_lot, cream, warehouse):
    make_lot(cream, "100")
    client = api_client_for("magasinier")
    created = client.post("/api/stocks/inventories/", {"site": warehouse.id}, format="json").json()

    # Pendant le comptage, la quantité théorique est cachée…
    assert created["lines"][0]["expected_quantity"] is None
    line_id = created["lines"][0]["id"]
    client.post(
        f"/api/stocks/inventories/{created['id']}/count/",
        {"lines": [{"id": line_id, "counted_quantity": "97"}]},
        format="json",
    )
    # … sauf à l'étape des écarts, juste avant la validation
    preview = client.get(f"/api/stocks/inventories/{created['id']}/?show_differences=1").json()
    assert preview["lines"][0]["difference"] == "-3.000"

    validated = client.post(f"/api/stocks/inventories/{created['id']}/validate/").json()
    assert validated["status"] == "valide"
    assert validated["lines"][0]["expected_quantity"] == "100.000"


def test_seul_le_magasinier_fait_l_inventaire(api_client_for, warehouse):
    response = api_client_for("qualite").post(
        "/api/stocks/inventories/", {"site": warehouse.id}, format="json"
    )
    assert response.status_code == 403


def test_alertes_ouvertes_et_traitement(api_client_for, make_lot, cream):
    make_lot(cream, expiry_in=1)
    from stocks.monitoring import run_daily_checks

    run_daily_checks()
    client = api_client_for("qualite")
    # Péremption proche + relevé manquant (aucun relevé dans la quarantaine)
    assert client.get("/api/stocks/alerts/open-count/").json() == {"count": 2}

    alert_id = client.get("/api/stocks/alerts/?state=open&alert_type=peremption_proche").json()[
        "results"
    ][0]["id"]
    refused = client.post(f"/api/stocks/alerts/{alert_id}/resolve/", {}, format="json")
    assert refused.status_code == 400
    done = client.post(
        f"/api/stocks/alerts/{alert_id}/resolve/", {"comment": "Lot consommé"}, format="json"
    ).json()
    assert done["is_open"] is False
    assert client.get("/api/stocks/alerts/open-count/").json() == {"count": 1}

    commercial = api_client_for("commercial")
    assert (
        commercial.post(f"/api/stocks/alerts/{alert_id}/resolve/", {"comment": "x"}).status_code
        == 403
    )


def test_donnees_de_demo_de_la_surveillance(db):
    call_command("charger_donnees_demo", sans_historique=True)
    from stocks.models import Lot, TemperatureReading

    assert TemperatureReading.objects.filter(is_compliant=False).count() == 1
    assert Alert.objects.filter(alert_type="ecart_temperature").count() == 1
    inv = Inventory.objects.get()
    assert inv.status == "valide"
    peas = Lot.objects.get(supplier_lot_number="SA-PP-2291")
    assert peas.quantity == Decimal("398")
    call_command("charger_donnees_demo", sans_historique=True)
    assert Inventory.objects.count() == 1
