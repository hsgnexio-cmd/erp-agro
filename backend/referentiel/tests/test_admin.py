"""Les écrans de saisie de l'administration s'ouvrent sans erreur."""

import pytest
from django.core.management import call_command
from django.urls import reverse

MODELS = [
    "site",
    "location",
    "productfamily",
    "materialcategory",
    "allergen",
    "customer",
    "customerwarehouse",
    "recipe",
    "article",
    "billofmaterials",
    "supplier",
]


@pytest.fixture
def admin_client_with_data(admin_client):
    call_command("charger_donnees_demo", sans_historique=True)
    return admin_client


@pytest.mark.parametrize("model", MODELS)
def test_les_listes_s_affichent(admin_client_with_data, model):
    response = admin_client_with_data.get(reverse(f"admin:referentiel_{model}_changelist"))
    assert response.status_code == 200


def test_la_fiche_article_et_son_historique_s_affichent(admin_client_with_data):
    from referentiel.models import Article

    article = Article.objects.get(code="PF-PAT-LASBOL-BRE-300")
    change = reverse("admin:referentiel_article_change", args=[article.id])
    history = reverse("admin:referentiel_article_history", args=[article.id])
    assert admin_client_with_data.get(change).status_code == 200
    assert admin_client_with_data.get(history).status_code == 200


def test_la_nomenclature_s_affiche(admin_client_with_data):
    from referentiel.models import BillOfMaterials

    bom = BillOfMaterials.objects.get(article__code="SF-BECHAMEL")
    url = reverse("admin:referentiel_billofmaterials_change", args=[bom.id])
    assert admin_client_with_data.get(url).status_code == 200
