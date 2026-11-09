"""API des prévisions : droits par rôle, saisie et consultation."""

from datetime import timedelta

from previsions import forecast
from previsions.models import ForecastAdjustment, Promotion
from previsions.tests.conftest import moment, week

URL = "/api/previsions/"


def test_tous_les_roles_consultent_la_prevision(
    api_client_for, private_label_customer, finished_product, place_order
):
    place_order(private_label_customer, finished_product, 1200, week(-1) + timedelta(1))
    response = api_client_for("production").get(
        f"{URL}forecast/", {"customer": private_label_customer.pk}
    )
    assert response.status_code == 200
    data = response.json()
    assert [w["week"] for w in data["weeks"]] == [str(w) for w in forecast.horizon()]
    row = next(r for r in data["rows"] if r["article"] == finished_product.pk)
    assert row["customer_code"] == "ENS2"
    assert row["cells"][0]["quantity"] == "1200"
    assert row["cells"][0]["base"] == "1200"


def test_le_commercial_saisit_une_promotion_annoncee_tard(
    api_client_for, private_label_customer, finished_product
):
    response = api_client_for("commercial").post(
        f"{URL}promotions/",
        {
            "customer": private_label_customer.pk,
            "article": finished_product.pk,
            "first_week": str(week(3)),
            "last_week": str(week(4)),
            "coefficient": "2.5",
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    assert response.json()["late_notice"] is True
    assert response.json()["first_week_label"] == forecast.week_label(week(3))


def test_un_magasinier_ne_saisit_ni_promotion_ni_correction(
    api_client_for, private_label_customer, finished_product
):
    client = api_client_for("magasinier")
    payload = {"customer": private_label_customer.pk, "article": finished_product.pk}
    assert client.post(f"{URL}promotions/", payload, format="json").status_code == 403
    assert client.post(f"{URL}adjustments/", payload, format="json").status_code == 403
    assert client.post(f"{URL}versions/", {}, format="json").status_code == 403
    assert Promotion.objects.count() == 0


def test_promotion_refusee_avec_message_lisible(
    api_client_for, private_label_customer, finished_product
):
    response = api_client_for("commercial").post(
        f"{URL}promotions/",
        {
            "customer": private_label_customer.pk,
            "article": finished_product.pk,
            "first_week": str(week(7)),
            "last_week": str(week(7)),
            "coefficient": "4",
        },
        format="json",
    )
    assert response.status_code == 400
    assert "×3" in str(response.json())


def test_annulation_d_une_promotion(api_client_for, private_label_customer, finished_product):
    promotion = forecast.create_promotion(
        customer=private_label_customer, article=finished_product,
        first_week=week(7), last_week=week(7), coefficient=2,
    )  # fmt: skip
    response = api_client_for("commercial").post(
        f"{URL}promotions/{promotion.pk}/cancel/", {"reason": "Annulée par l'enseigne"},
        format="json",
    )  # fmt: skip
    assert response.status_code == 200
    assert response.json()["cancel_reason"] == "Annulée par l'enseigne"
    assert response.json()["cancelled_by_name"] == "user-commercial"


def test_correction_puis_version_figee(api_client_for, private_label_customer, finished_product):
    client = api_client_for("commercial")
    response = client.post(
        f"{URL}adjustments/",
        {
            "customer": private_label_customer.pk,
            "article": finished_product.pk,
            "week": str(week(2)),
            "quantity": "480",
            "reason": "Ouverture de 4 magasins",
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    assert ForecastAdjustment.objects.get().created_by.username == "user-commercial"

    forecast_data = client.get(f"{URL}forecast/", {"customer": private_label_customer.pk}).json()
    cell = next(r for r in forecast_data["rows"] if r["article"] == finished_product.pk)["cells"][1]
    assert cell["quantity"] == "480.000"
    assert cell["adjustment"]["reason"] == "Ouverture de 4 magasins"

    response = client.post(f"{URL}versions/", {"comment": "S&OP"}, format="json")
    assert response.status_code == 201
    assert response.json()["line_count"] == 1
    detail = client.get(f"{URL}versions/{response.json()['id']}/").json()
    assert detail["lines"][0]["adjusted"] is True


def test_fiabilite_par_semaine(
    api_client_for, private_label_customer, finished_product, place_order
):
    place_order(private_label_customer, finished_product, 1200, week(-3) + timedelta(1))
    forecast.create_version(at=moment(week(-2)))
    place_order(private_label_customer, finished_product, 1000, week(-1) + timedelta(1))
    data = api_client_for("direction").get(f"{URL}accuracy/").json()
    assert data["target"] == "80"
    # La semaine en cours apparaît aussi, mais non terminée : elle ne compte pas
    assert [(w["label"], w["accuracy"], w["complete"]) for w in data["weeks"]] == [
        (forecast.week_label(week(-1)), "80.0", True),
        (forecast.week_label(week(0)), None, False),
    ]
    assert data["accuracy"] == "80.0"
