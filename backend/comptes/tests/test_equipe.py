"""Équipe de démonstration : un compte par personne, avec son rôle et sa fonction."""

from django.contrib.auth import get_user_model
from django.core.management import call_command

from comptes import demo_users


def test_l_equipe_est_creee_avec_ses_roles(db, client):
    counts = demo_users.load_demo_data("mot-de-passe-test")
    assert counts["comptes de démonstration créés"] == len(demo_users.TEAM)
    users = get_user_model().objects
    claire = users.get(username="claire.lebihan")
    assert claire.job_title == "Responsable qualité"
    assert list(claire.groups.values_list("name", flat=True)) == ["qualite"]
    assert not claire.is_staff and not claire.is_superuser
    # Deux responsables de production, un par usine
    assert users.filter(groups__name="production").count() == 2

    # Connexion avec le mot de passe de démonstration ; le rôle et la fonction sont renvoyés
    response = client.post(
        "/api/auth/login/",
        {"username": "claire.lebihan", "password": "mot-de-passe-test"},
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    me = client.get("/api/auth/me/").json()
    assert me["roles"] == ["qualite"] and me["job_title"] == "Responsable qualité"


def test_relancer_ne_cree_pas_de_doublon_ni_ne_change_un_mot_de_passe(db):
    demo_users.load_demo_data("mot-de-passe-test")
    user = get_user_model().objects.get(username="marc.guillou")
    user.set_password("change-par-marc")
    user.save()
    counts = demo_users.load_demo_data("mot-de-passe-test")
    assert counts["comptes de démonstration créés"] == 0
    assert get_user_model().objects.get(username="marc.guillou").check_password("change-par-marc")


def test_sans_mot_de_passe_aucun_compte(db, settings):
    settings.DEMO_USERS_PASSWORD = ""
    counts = demo_users.load_demo_data()
    assert "DEMO_USERS_PASSWORD" in counts["comptes de démonstration"]
    assert not get_user_model().objects.exists()
    call_command("creer_comptes_demo")  # ne plante pas non plus
