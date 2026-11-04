"""API du référentiel et droits par rôle (CLAUDE.md, section 9)."""

import pytest
from rest_framework.test import APIClient

from referentiel.models import Allergen

CUSTOMER = {
    "code": "ENS7",
    "name": "Nouvelle enseigne",
    "customer_type": "hyper",
    "sells_brand": True,
    "sells_private_label": False,
    "min_remaining_shelf_life_pct": "70.00",
}


def test_il_faut_etre_connecte(db):
    response = APIClient().get("/api/referentiel/articles/")
    assert response.status_code == 403


@pytest.mark.parametrize(
    "role", ["admin", "direction", "acheteur", "magasinier", "production", "qualite", "commercial"]
)
def test_tous_les_roles_peuvent_consulter(api_client_for, finished_product, role):
    response = api_client_for(role).get("/api/referentiel/articles/")
    assert response.status_code == 200
    assert response.json()["results"][0]["code"] == "PF-PAT-LASBOL-BRE-300"


@pytest.mark.parametrize(
    ("role", "expected"),
    [("commercial", 201), ("admin", 201), ("acheteur", 403), ("direction", 403)],
)
def test_seuls_commercial_et_admin_creent_une_enseigne(api_client_for, role, expected):
    response = api_client_for(role).post("/api/referentiel/customers/", CUSTOMER, format="json")
    assert response.status_code == expected


@pytest.mark.parametrize(("role", "expected"), [("acheteur", 201), ("commercial", 403)])
def test_seuls_acheteur_et_admin_creent_un_fournisseur(api_client_for, role, expected):
    data = {"code": "FOU-099", "name": "Nouveau fournisseur", "lead_time_days": 3}
    response = api_client_for(role).post("/api/referentiel/suppliers/", data, format="json")
    assert response.status_code == expected


def test_on_ne_supprime_pas_une_donnee_de_reference(api_client_for, finished_product):
    response = api_client_for("admin").delete(f"/api/referentiel/articles/{finished_product.id}/")
    assert response.status_code == 405


def test_une_regle_metier_renvoie_une_erreur_claire(api_client_for, recipe, brand_only_customer):
    data = {
        "name": "Lasagnes Proxi",
        "article_type": "PF",
        "unit": "u",
        "recipe": recipe.id,
        "brand_customer": brand_only_customer.id,
        "format_size": 300,
        "shelf_life_days": 14,
    }
    response = api_client_for("production").post("/api/referentiel/articles/", data, format="json")
    assert response.status_code == 400
    assert "MDD" in response.json()["brand_customer"][0]


def test_creation_d_un_produit_fini_par_l_api(api_client_for, recipe):
    data = {
        "name": "Lasagnes 300 g",
        "article_type": "PF",
        "unit": "u",
        "recipe": recipe.id,
        "format_size": 300,
        "shelf_life_days": 14,
    }
    response = api_client_for("production").post("/api/referentiel/articles/", data, format="json")
    assert response.status_code == 201
    assert response.json()["code"] == "PF-PAT-LASBOL-BRE-300"
    assert response.json()["date_type"] == "DLC"


def test_seule_la_qualite_modifie_les_allergenes(api_client_for, cream):
    lait = Allergen.objects.get(code="lait")
    url = f"/api/referentiel/articles/{cream.id}/"

    response = api_client_for("production").patch(url, {"allergens": [lait.id]}, format="json")
    assert response.status_code == 403

    response = api_client_for("qualite").patch(url, {"allergens": [lait.id]}, format="json")
    assert response.status_code == 200
    assert response.json()["allergen_names"] == ["Lait"]


def test_pas_d_allergene_saisi_sur_un_produit_fini(api_client_for, finished_product):
    lait = Allergen.objects.get(code="lait")
    response = api_client_for("qualite").patch(
        f"/api/referentiel/articles/{finished_product.id}/", {"allergens": [lait.id]}, format="json"
    )
    assert response.status_code == 400


def test_filtrer_les_articles_par_type(api_client_for, finished_product, cream):
    response = api_client_for("direction").get("/api/referentiel/articles/?article_type=MP")
    codes = [a["code"] for a in response.json()["results"]]
    assert codes == ["MP-LAI-CREME35"]


def test_rechercher_un_article(api_client_for, finished_product, cream):
    response = api_client_for("direction").get("/api/referentiel/articles/?search=crème")
    assert [a["code"] for a in response.json()["results"]] == ["MP-LAI-CREME35"]


def test_les_groupes_ont_les_droits_de_l_administration(db):
    from django.contrib.auth.models import Group

    commercial = Group.objects.get(name="commercial")
    codenames = set(commercial.permissions.values_list("codename", flat=True))
    assert {"view_article", "add_customer", "change_customer"} <= codenames
    assert "change_article" not in codenames
    assert "delete_customer" not in codenames
