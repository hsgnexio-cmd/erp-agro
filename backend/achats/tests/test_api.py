"""API des achats et droits par rôle, avec un parcours complet commande → réception."""

from datetime import timedelta

import pytest
from django.utils import timezone


@pytest.fixture
def order_payload(warehouse, supplier, cream_at_supplier, cream):
    return {
        "supplier": supplier.id,
        "delivery_site": warehouse.id,
        "lines": [{"article": cream.id, "quantity": "100"}],
    }


@pytest.mark.parametrize(
    ("role", "expected"),
    [("acheteur", 201), ("admin", 201), ("magasinier", 403), ("direction", 403)],
)
def test_seuls_acheteur_et_admin_creent_une_commande(api_client_for, order_payload, role, expected):
    response = api_client_for(role).post("/api/achats/orders/", order_payload, format="json")
    assert response.status_code == expected


def test_une_erreur_de_ligne_est_expliquee(api_client_for, order_payload):
    order_payload["lines"][0]["quantity"] = "100"
    order_payload["lines"].append(
        {"article": order_payload["lines"][0]["article"], "quantity": "5"}
    )
    response = api_client_for("acheteur").post("/api/achats/orders/", order_payload, format="json")
    assert response.status_code == 400
    assert "MP-LAI-CREME35" in response.json()["lines"][0]


def test_catalogue_du_fournisseur(api_client_for, supplier, cream_at_supplier):
    response = api_client_for("acheteur").get(f"/api/achats/catalog/?supplier={supplier.id}")
    assert response.json() == [
        {
            "article": cream_at_supplier.article.id,
            "article_code": "MP-LAI-CREME35",
            "article_name": "Crème 35 %",
            "unit": "kg",
            "min_order_quantity": None,
            "unit_price": "4.2000",
        }
    ]


def test_parcours_complet_commande_reception(api_client_for, order_payload, quarantine, make_user):
    buyer = api_client_for("acheteur")
    created = buyer.post("/api/achats/orders/", order_payload, format="json").json()
    assert created["status"] == "brouillon"
    assert created["total_amount"] == "420.00"

    # Une commande en brouillon se modifie
    order_payload["lines"][0]["quantity"] = "120"
    updated = buyer.put(f"/api/achats/orders/{created['id']}/", order_payload, format="json")
    assert updated.json()["lines"][0]["quantity"] == "120.000"

    sent = buyer.post(f"/api/achats/orders/{created['id']}/send/").json()
    assert sent["status"] == "envoyee"

    # Une commande envoyée ne se modifie plus
    refused = buyer.put(f"/api/achats/orders/{created['id']}/", order_payload, format="json")
    assert refused.status_code == 400

    reception_payload = {
        "order": created["id"],
        "location": quarantine.id,
        "delivery_note_number": "BL-2026-118",
        "lines": [
            {
                "order_line": sent["lines"][0]["id"],
                "quantity": "120",
                "supplier_lot_number": "CB-0412",
                "expiry_date": str(timezone.localdate() + timedelta(days=20)),
                "temperature": "3.2",
            }
        ],
    }
    # L'acheteur ne réceptionne pas : c'est le rôle du magasinier
    assert (
        buyer.post("/api/achats/receptions/", reception_payload, format="json").status_code == 403
    )

    response = api_client_for("magasinier").post(
        "/api/achats/receptions/", reception_payload, format="json"
    )
    assert response.status_code == 201
    reception = response.json()
    assert reception["is_compliant"] is True
    assert reception["lines"][0]["lot_status"] == "quarantaine"
    assert reception["received_by_name"] == "user-magasinier"

    order = buyer.get(f"/api/achats/orders/{created['id']}/").json()
    assert order["status"] == "soldee"
    assert order["lines"][0]["received_quantity"] == "120.000"

    lots = api_client_for("qualite").get("/api/stocks/lots/?status=quarantaine").json()
    assert lots["count"] == 1
    assert lots["results"][0]["quantity"] == "120.000"
    assert lots["results"][0]["reception_number"] == reception["number"]


def test_reception_non_conforme_par_l_api(
    api_client_for, make_order, cream_at_supplier, cream, quarantine
):
    order = make_order((cream, "50"))
    response = api_client_for("magasinier").post(
        "/api/achats/receptions/",
        {
            "order": order.id,
            "location": quarantine.id,
            "delivery_note_number": "BL-9",
            "lines": [
                {
                    "order_line": order.lines.get().id,
                    "quantity": "50",
                    "supplier_lot_number": "CB-1",
                    "expiry_date": str(timezone.localdate() + timedelta(days=20)),
                    "temperature": "7",
                }
            ],
        },
        format="json",
    )
    body = response.json()
    assert body["is_compliant"] is False
    assert body["lines"][0]["lot_status"] == "bloque"
    assert "Température" in body["lines"][0]["non_compliance_reasons"]


def test_annuler_par_l_api(api_client_for, make_order, cream_at_supplier, cream):
    order = make_order((cream, "50"))
    response = api_client_for("acheteur").post(f"/api/achats/orders/{order.id}/cancel/")
    assert response.json()["status"] == "annulee"


def test_les_lots_ne_se_creent_pas_par_l_api(api_client_for):
    """Un lot naît uniquement d'une opération (réception…), jamais d'une saisie directe."""
    response = api_client_for("admin").post("/api/stocks/lots/", {}, format="json")
    assert response.status_code == 405  # opération inexistante
