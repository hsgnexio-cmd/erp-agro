from rest_framework.test import APIClient


def test_connexion_et_profil(make_user):
    make_user("qualite", username="claire")
    client = APIClient()

    response = client.post(
        "/api/auth/login/", {"username": "claire", "password": "motdepasse-test"}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["roles"] == ["qualite"]

    me = client.get("/api/auth/me/")
    assert me.json()["username"] == "claire"


def test_mauvais_mot_de_passe(make_user):
    make_user("qualite", username="claire")
    response = APIClient().post(
        "/api/auth/login/", {"username": "claire", "password": "faux"}, format="json"
    )
    assert response.status_code == 400
    assert "incorrect" in response.json()["detail"]


def test_deconnexion(make_user):
    make_user(username="claire")
    client = APIClient()
    client.post(
        "/api/auth/login/", {"username": "claire", "password": "motdepasse-test"}, format="json"
    )
    assert client.post("/api/auth/logout/").status_code == 204
    assert client.get("/api/auth/me/").status_code == 403


def test_le_cookie_csrf_est_depose(db):
    response = APIClient().get("/api/auth/csrf/")
    assert "csrftoken" in response.cookies


def test_connexion_depuis_le_front_end_avec_protection_csrf(make_user):
    """Le navigateur envoie l'origine http://localhost:5173 : elle doit être acceptée."""
    from django.test import Client

    make_user(username="claire")
    client = Client(enforce_csrf_checks=True)
    client.get("/api/auth/csrf/")
    response = client.post(
        "/api/auth/login/",
        {"username": "claire", "password": "motdepasse-test"},
        content_type="application/json",
        headers={
            "X-CSRFToken": client.cookies["csrftoken"].value,
            "Origin": "http://localhost:5173",
        },
    )
    assert response.status_code == 200


def test_connexion_refusee_depuis_un_site_inconnu(make_user):
    from django.test import Client

    make_user(username="claire")
    client = Client(enforce_csrf_checks=True)
    client.get("/api/auth/csrf/")
    response = client.post(
        "/api/auth/login/",
        {"username": "claire", "password": "motdepasse-test"},
        content_type="application/json",
        headers={
            "X-CSRFToken": client.cookies["csrftoken"].value,
            "Origin": "http://site-pirate.example",
        },
    )
    assert response.status_code == 403
