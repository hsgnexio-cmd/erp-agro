"""API de préparation et d'expédition : parcours complet et droits (partie 7b)."""

from datetime import timedelta

import pytest
from django.utils import timezone

TODAY = timezone.localdate


def _prepare_payload(client, order):
    """Reprend la proposition FEFO telle quelle (ce que fait l'écran de préparation)."""
    proposal = client.get(f"/api/ventes/orders/{order.id}/picking-proposal/").json()
    return {
        "lines": [
            {
                "order_line": line["order_line"],
                "lot": lot["lot"],
                "location": lot["location"],
                "quantity": lot["suggested"],
            }
            for line in proposal["lines"]
            for lot in line["lots"]
            if float(lot["suggested"]) > 0
        ]
    }


def test_parcours_complet_par_l_api(api_client_for, make_order, finished_product, stock):
    client = api_client_for("magasinier")
    order = make_order([(finished_product, "400")])

    proposal = client.get(f"/api/ventes/orders/{order.id}/picking-proposal/")
    assert proposal.status_code == 200
    (line,) = proposal.json()["lines"]
    assert line["min_expiry_date"] == (TODAY() + timedelta(days=12)).isoformat()
    assert [lot["suggested"] for lot in line["lots"]] == ["300.000", "100.000"]
    assert [lot["lot_number"] for lot in line["too_short"]] == [stock["court"].number]

    prepared = client.post(
        f"/api/ventes/orders/{order.id}/prepare/", _prepare_payload(client, order), format="json"
    )
    assert prepared.status_code == 201, prepared.json()
    shipment = prepared.json()
    assert shipment["status"] == "preparee"
    assert client.get(f"/api/ventes/orders/{order.id}/").json()["status"] == "en_preparation"

    shipped = client.post(
        f"/api/ventes/shipments/{shipment['id']}/ship/",
        {"carrier": "Transports Bretagne Froid", "temperature": "3.2"},
        format="json",
    )
    assert shipped.status_code == 200, shipped.json()
    data = shipped.json()
    assert data["status"] == "expediee"
    assert data["on_time"] is True
    assert data["pallet_count"] == 1
    assert len(data["pallets"][0]["sscc"]) == 18
    assert data["summary"][0]["missing"] == "0.000"

    order_data = client.get(f"/api/ventes/orders/{order.id}/").json()
    assert order_data["status"] == "expediee"
    assert order_data["lines"][0]["shipped_quantity"] == "400.000"
    assert order_data["shipments"][0]["number"] == shipment["number"]

    listing = client.get("/api/ventes/shipments/").json()
    assert listing["results"][0]["number"] == shipment["number"]

    rate = client.get(
        "/api/ventes/service-rate/",
        {"start": TODAY().isoformat(), "end": (TODAY() + timedelta(days=7)).isoformat()},
    ).json()
    assert rate["target"] == "98.5"
    assert rate["customers"][0]["rate"] == "100.0"


def test_refus_pour_temperature_par_l_api(api_client_for, make_order, finished_product, stock):
    client = api_client_for("magasinier")
    order = make_order([(finished_product, "100")])
    shipment = client.post(
        f"/api/ventes/orders/{order.id}/prepare/", _prepare_payload(client, order), format="json"
    ).json()
    response = client.post(
        f"/api/ventes/shipments/{shipment['id']}/ship/",
        {"carrier": "TBF", "temperature": "5.8"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "refusee"
    assert "5,8 °C" in response.json()["refusal_reason"]


def test_erreur_metier_lisible(api_client_for, make_order, finished_product, stock):
    client = api_client_for("magasinier")
    order = make_order([(finished_product, "100")])
    response = client.post(
        f"/api/ventes/orders/{order.id}/prepare/",
        {
            "lines": [
                {
                    "order_line": order.lines.get().id,
                    "lot": stock["second"].id,
                    "location": stock["second"].location.id,
                    "quantity": "100",
                }
            ]
        },
        format="json",
    )
    assert response.status_code == 400
    assert "hors FEFO" in str(response.json())


@pytest.mark.parametrize(("role", "expected"), [("magasinier", 201), ("commercial", 403)])
def test_seul_le_magasinier_prepare(api_client_for, make_order, finished_product, stock, role,
                                    expected):  # fmt: skip
    client = api_client_for(role)
    order = make_order([(finished_product, "100")])
    response = client.post(
        f"/api/ventes/orders/{order.id}/prepare/", _prepare_payload(client, order), format="json"
    )
    assert response.status_code == expected


@pytest.mark.parametrize(("role", "expected"), [("magasinier", 200), ("commercial", 403)])
def test_seul_le_magasinier_expedie(api_client_for, make_order, finished_product, stock, role,
                                    expected):  # fmt: skip
    warehouse_client = api_client_for("magasinier")
    order = make_order([(finished_product, "100")])
    shipment = warehouse_client.post(
        f"/api/ventes/orders/{order.id}/prepare/",
        _prepare_payload(warehouse_client, order),
        format="json",
    ).json()
    client = warehouse_client if role == "magasinier" else api_client_for(role)
    response = client.post(
        f"/api/ventes/shipments/{shipment['id']}/ship/",
        {"carrier": "TBF", "temperature": "3"},
        format="json",
    )
    assert response.status_code == expected


def test_le_commercial_annule_toujours_ses_commandes(api_client_for, make_order, finished_product):
    order = make_order([(finished_product, "100")])
    response = api_client_for("commercial").post(f"/api/ventes/orders/{order.id}/cancel/")
    assert response.status_code == 200


def test_annuler_une_preparation_par_l_api(api_client_for, make_order, finished_product, stock):
    client = api_client_for("magasinier")
    order = make_order([(finished_product, "100")])
    shipment = client.post(
        f"/api/ventes/orders/{order.id}/prepare/", _prepare_payload(client, order), format="json"
    ).json()
    response = client.post(
        f"/api/ventes/shipments/{shipment['id']}/cancel/", {"reason": "Erreur"}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["status"] == "annulee"
