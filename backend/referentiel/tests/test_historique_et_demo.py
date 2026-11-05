"""Historique des modifications (règle 12) et données de démonstration."""

from django.core.management import call_command

from referentiel.models import Article, BOMLine, Customer


def test_chaque_modification_est_historisee(api_client_for, cream):
    client = api_client_for("qualite")
    client.patch(f"/api/referentiel/articles/{cream.id}/", {"shelf_life_days": 18}, format="json")

    history = cream.history.order_by("history_date")
    assert history.count() == 2  # création puis modification
    last = history.last()
    assert last.shelf_life_days == 18
    assert last.history_user.username == "user-qualite"
    assert history.first().shelf_life_days == 21


def test_les_donnees_de_demo_se_chargent_sans_doublon(db):
    call_command("charger_donnees_demo", sans_historique=True)
    call_command("charger_donnees_demo", sans_historique=True)

    assert Customer.objects.count() == 6
    assert Article.objects.filter(article_type="PF").count() == 22
    assert Article.objects.filter(code="PF-PAT-LASBOL-ENS2-1000").exists()
    assert not Article.objects.filter(brand_customer__code="ENS4").exists()


def test_la_creme_est_utilisee_dans_plusieurs_recettes(db):
    """Prépare le scénario de rappel produit de la phase 5."""
    call_command("charger_donnees_demo", sans_historique=True)
    used_in = set(
        BOMLine.objects.filter(component__code="MP-LAI-CREME35").values_list(
            "bom__article__code", flat=True
        )
    )
    assert {"SF-BECHAMEL", "SF-PUREE", "PF-GRA-GRADAU-BRE-1000"} <= used_in
