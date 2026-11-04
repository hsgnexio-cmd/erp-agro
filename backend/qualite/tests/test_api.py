"""API qualité, fabrication et expédition : droits par rôle."""

import pytest


def test_tracabilite_par_l_api(api_client_for, chain):
    body = (
        api_client_for("commercial")
        .get(f"/api/qualite/traceability/?lot={chain['lasagna'].number.lower()}")
        .json()
    )
    assert body["upstream"]["lot_number"] == chain["lasagna"].number
    assert len(body["upstream"]["children"]) == 2
    assert body["downstream"]["shipments"][0]["customer_code"] == "ENS2"


def test_simulation_par_l_api(api_client_for, chain):
    body = (
        api_client_for("direction")
        .get(f"/api/qualite/recall-simulation/?lot={chain['cream_a'].number}")
        .json()
    )
    assert len(body["lots"]) == 3
    assert body["customers"] == [
        {"code": "ENS2", "name": "Marché Plus", "deliveries": 1, "quantities": {"u": "600.000"}}
    ]


@pytest.mark.parametrize(("role", "expected"), [("qualite", 201), ("magasinier", 403)])
def test_seule_la_qualite_lance_un_rappel(api_client_for, chain, role, expected):
    response = api_client_for(role).post(
        "/api/qualite/recalls/",
        {"lot_number": chain["cream_a"].number, "reason": "Contamination"},
        format="json",
    )
    assert response.status_code == expected


def test_export_csv_par_l_api(api_client_for, chain):
    client = api_client_for("qualite")
    recall = client.post(
        "/api/qualite/recalls/",
        {"lot_number": chain["cream_a"].number, "reason": "Contamination"},
        format="json",
    ).json()
    response = client.get(f"/api/qualite/recalls/{recall['id']}/export/")
    assert response["Content-Type"].startswith("text/csv")
    assert "ENS2-E01" in response.content.decode("utf-8")


def test_lot_inconnu(api_client_for, db):
    response = api_client_for("qualite").get("/api/qualite/traceability/?lot=LR-000000-0000")
    assert response.status_code == 400
    assert "introuvable" in response.json()["lot"][0]


def test_l_expedition_directe_n_existe_plus(api_client_for, chain):
    """Depuis la partie 7b, toute expédition passe par la préparation d'une commande client."""
    response = api_client_for("magasinier").post(
        "/api/ventes/shipments/",
        {
            "lot": chain["lasagna"].id,
            "location": chain["cold"].id,
            "quantity": "10",
            "warehouse": chain["warehouse"].id,
        },
        format="json",
    )
    assert response.status_code == 405


def test_allergenes_par_l_api(api_client_for, chain, finished_product, cream):
    from referentiel.models import Allergen

    cream.allergens.add(Allergen.objects.get(code="lait"))
    body = api_client_for("commercial").get(
        f"/api/qualite/allergens/?article={finished_product.id}"
    )
    assert body.json() == [
        {"code": "lait", "name": "Lait", "sources": [["SF-BECHAMEL", "MP-LAI-CREME35"]]}
    ]
