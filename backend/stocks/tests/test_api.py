"""API des stocks et droits : la qualité change les statuts, le magasinier déplace."""

from decimal import Decimal

import pytest
from django.core.management import call_command

from stocks import services


@pytest.mark.parametrize(
    ("role", "expected"), [("qualite", 200), ("admin", 200), ("magasinier", 403)]
)
def test_seule_la_qualite_libere(api_client_for, make_lot, cream, role, expected):
    lot = make_lot(cream)
    response = api_client_for(role).post(f"/api/stocks/lots/{lot.id}/release/")
    assert response.status_code == expected


def test_bloquer_puis_detruire_par_l_api(api_client_for, make_lot, cream):
    lot = make_lot(cream)
    client = api_client_for("qualite")

    refused = client.post(f"/api/stocks/lots/{lot.id}/block/", {}, format="json")
    assert refused.status_code == 400
    assert "motif" in refused.json()["reason"][0]

    blocked = client.post(
        f"/api/stocks/lots/{lot.id}/block/", {"reason": "Rappel fournisseur"}, format="json"
    ).json()
    assert blocked["status"] == "bloque"

    destroyed = client.post(
        f"/api/stocks/lots/{lot.id}/destroy/", {"reason": "Destruction"}, format="json"
    ).json()
    assert destroyed["status"] == "detruit"
    assert destroyed["quantity"] == "0.000"
    assert [c["to_status"] for c in destroyed["status_changes"]] == ["detruit", "bloque"]


@pytest.mark.parametrize(("role", "expected"), [("magasinier", 200), ("qualite", 403)])
def test_seul_le_magasinier_transfere(api_client_for, make_lot, cream, cold_room, role, expected):
    lot = make_lot(cream, "100")
    response = api_client_for(role).post(
        f"/api/stocks/lots/{lot.id}/transfer/",
        {"from_location": lot.location.id, "to_location": cold_room.id, "quantity": "30"},
        format="json",
    )
    assert response.status_code == expected
    if expected == 200:
        stock = {
            row["location_code"]: row["quantity"] for row in response.json()["stock_by_location"]
        }
        assert stock == {"MPE-FP-01": "30.000", "MPE-QUAR": "70.000"}


def test_correction_par_l_api(api_client_for, make_lot, cream):
    lot = make_lot(cream, "100")
    movement = lot.movements.get()
    response = api_client_for("magasinier").post(
        f"/api/stocks/movements/{movement.id}/correct/",
        {"quantity": "10", "reason": "Erreur de pesée"},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["quantity"] == "-10.000"


def test_fefo_par_l_api(api_client_for, make_lot, cream, cold_room):
    for days in (9, 4):
        services.release_lot(make_lot(cream, "100", expiry_in=days))
    response = api_client_for("production").get(
        "/api/stocks/fefo/?article=mp-lai-creme35&site=MPE&quantity=120"
    )
    body = response.json()
    assert [Decimal(line["take"]) for line in body["lines"]] == [100, 20]
    assert Decimal(body["missing"]) == 0


def test_etat_des_stocks_par_l_api(api_client_for, make_lot, cream):
    make_lot(cream, "40")
    rows = api_client_for("direction").get("/api/stocks/summary/?site=MPE").json()
    assert rows[0]["quarantine"] == "40.000"


def test_donnees_de_demo_des_stocks(db):
    call_command("charger_donnees_demo")
    from stocks.models import Lot

    cream_lot = Lot.objects.get(supplier_lot_number="CB-0412")
    stock = {loc.code: qty for loc, qty in services.stock_by_location(cream_lot)}
    assert stock["MPE-FP-01"] == Decimal("250")
    # 150 kg envoyés à l'usine NAN (ensuite consommés en partie par les fabrications de démo)
    sent = cream_lot.movements.get(movement_type="transfert_entree", location__code="NAN-CF-MP")
    assert sent.quantity == Decimal("150")
    assert Lot.objects.get(supplier_lot_number="VO-26-3321").status == "detruit"
    # Relancer le chargement ne refait pas les mouvements
    call_command("charger_donnees_demo")
    assert cream_lot.movements.filter(movement_type="transfert_entree").count() == 2
