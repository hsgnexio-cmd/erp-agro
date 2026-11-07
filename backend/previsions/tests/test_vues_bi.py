"""Vues bi des prévisions : mêmes résultats que le calcul métier (lues par le tableau de bord
et par Power BI)."""

from datetime import timedelta

from django.db import connection
from django.utils import timezone

from pilotage import indicators
from previsions import forecast
from previsions.tests.conftest import moment, week


def _rows(query: str, params=()):
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()


def test_vue_fiabilite_identique_au_calcul_metier(
    private_label_customer, brand_only_customer, finished_product, mdd_lasagna, place_order
):
    # Trois semaines d'historique, une version figée chaque lundi, une promotion, une correction
    for offset, quantities in (
        (-4, (1200, 240, 600)),
        (-3, (1080, 360, 720)),
        (-2, (1320, 0, 480)),
    ):
        place_order(
            private_label_customer, finished_product, quantities[0], week(offset) + timedelta(1)
        )
        if quantities[1]:
            place_order(
                brand_only_customer, finished_product, quantities[1], week(offset) + timedelta(2)
            )
        place_order(private_label_customer, mdd_lasagna, quantities[2], week(offset) + timedelta(3))
        forecast.create_version(at=moment(week(offset + 1)))
    place_order(private_label_customer, finished_product, 1440, week(-1) + timedelta(1))
    place_order(brand_only_customer, finished_product, 120, week(-1) + timedelta(4))

    today = timezone.localdate()
    start = week(-4)
    for customer_id in (None, private_label_customer.pk, brand_only_customer.pk):
        expected = {
            result.week: result for result in forecast.accuracy_by_week(start, today, customer_id)
        }
        where = "" if customer_id is None else f" AND customer_id = {customer_id}"
        rows = _rows(
            "SELECT week_start, max(version_number), sum(forecast_quantity), "
            "sum(actual_quantity), sum(abs_error), bool_and(is_complete) "
            f"FROM bi.fact_forecast_accuracy WHERE week_start >= %s{where} GROUP BY week_start",
            [start],
        )
        view = {row[0]: row[1:] for row in rows}
        for monday, result in expected.items():
            if not result.actual and not result.forecast:
                continue  # rien de prévu ni commandé : aucune ligne dans la vue
            assert view[monday] == (
                result.version.number, result.forecast, result.actual, result.abs_error,
                result.complete,
            ), (monday, customer_id)  # fmt: skip

        # Le tableau de bord lit la vue : même fiabilité globale que le calcul métier
        value, _ = indicators.forecast_accuracy(start, today, customer_id)
        assert value == forecast.overall_accuracy(list(expected.values()))


def test_vue_des_lignes_de_prevision(private_label_customer, finished_product, place_order):
    place_order(private_label_customer, finished_product, 1200, week(-1) + timedelta(1))
    version = forecast.create_version()
    rows = _rows(
        "SELECT version_number, week_start, week_label, quantity, is_adjusted "
        "FROM bi.fact_forecast ORDER BY week_start"
    )
    assert len(rows) == 8
    first = rows[0]
    assert first[0] == version.number and first[1] == week(1)
    assert first[2] == f"{week(1).isocalendar().year}-{forecast.week_label(week(1))}"
    assert first[3] == 1200 and first[4] is False
