"""TRS des lignes (phase 10) : plages de marche, arrêts, rebuts, calcul et vue bi."""

from datetime import datetime, time, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.utils import timezone

from pilotage import indicators
from production import oee, orders
from production.models import LineStop, StopCategory

D = Decimal
YESTERDAY = timezone.localdate() - timedelta(days=1)


def at(hour: int, minute: int = 0, day=None):
    return timezone.make_aware(datetime.combine(day or YESTERDAY, time(hour, minute)))


@pytest.fixture
def launched(lasagna_line, finished_product, factory, bechamel, stock_lot):
    """OF de lasagnes lancé sur L1 (2 400 unités / h), avec de la béchamel en stock."""
    stock_lot(bechamel, "5000")

    def _make(quantity="4800", day=None):
        order = orders.create_order(
            article=finished_product, planned_quantity=D(quantity),
            planned_date=day or YESTERDAY, line=lasagna_line,
        )  # fmt: skip
        return orders.launch_order(order)

    return _make


def declare(order, quantity, start, end, scrap="0", reason="", **kwargs):
    lot = order.article.bom.lines.get().component.lots.get()
    consumptions = [{"lot": lot, "location": lot.location, "quantity": D("1")}]
    return orders.declare_production(
        order, quantity=D(quantity), consumptions=consumptions, run_start=start, run_end=end,
        scrap_quantity=D(scrap), scrap_reason=reason, **kwargs,
    )  # fmt: skip


def stop(line, start, end, category=StopCategory.BREAKDOWN, **kwargs):
    return oee.record_stop(line=line, started_at=start, ended_at=end, category=category, **kwargs)


# --- Plages de marche et rebuts -----------------------------------------------------------


def test_plage_de_marche_et_rebut_enregistres(launched):
    declaration = declare(
        launched(), "4752", at(6), at(8, 30), scrap="48", reason="Opercule mal soudé"
    )
    assert (declaration.run_start, declaration.run_end) == (at(6), at(8, 30))
    assert declaration.scrap_quantity == D("48")
    assert declaration.lot.initial_quantity == D("4752")  # le rebut n'entre pas en stock


def test_plage_obligatoire_dans_l_application(launched):
    with pytest.raises(ValidationError) as exc:
        orders.declare_production(launched(), quantity=D("100"), consumptions=[], require_run=True)
    assert "début et de fin de marche" in str(exc.value)


@pytest.mark.parametrize(
    ("start", "end", "message"),
    [
        (at(8), at(7), "après le début"),
        (at(2), at(19), "16 h"),
        (at(6), timezone.now() + timedelta(hours=2), "futur"),
    ],
)
def test_plage_de_marche_incoherente_refusee(launched, start, end, message):
    with pytest.raises(ValidationError) as exc:
        declare(launched(), "100", start, end)
    assert message in str(exc.value)


def test_deux_of_ne_marchent_pas_en_meme_temps_sur_une_ligne(launched):
    declare(launched(), "2400", at(6), at(8))
    with pytest.raises(ValidationError) as exc:
        declare(launched(), "2400", at(7, 30), at(9))
    assert "déjà en marche" in str(exc.value)


def test_rebut_sans_motif_refuse(launched):
    with pytest.raises(ValidationError) as exc:
        declare(launched(), "2400", at(6), at(8), scrap="10")
    assert "motif du rebut" in str(exc.value)


# --- Arrêts --------------------------------------------------------------------------------


def test_arret_chevauchant_un_autre_refuse(lasagna_line):
    stop(lasagna_line, at(7), at(7, 30))
    with pytest.raises(ValidationError) as exc:
        stop(lasagna_line, at(7, 15), at(8), StopCategory.ADJUSTMENT)
    assert "Chevauchement" in str(exc.value)


def test_arret_futur_ou_d_un_of_d_une_autre_ligne_refuse(
    lasagna_line, bechamel, factory_site, factory
):
    bechamel_order = orders.create_order(
        article=bechamel, planned_quantity=D("100"), planned_date=YESTERDAY, site=factory_site
    )
    with pytest.raises(ValidationError) as exc:
        stop(lasagna_line, timezone.now(), timezone.now() + timedelta(hours=1))
    assert "future" in str(exc.value)
    with pytest.raises(ValidationError) as exc:
        stop(lasagna_line, at(6), at(7), production_order=bechamel_order)
    assert "n'est pas sur la ligne L1" in str(exc.value)


def test_un_arret_ne_se_modifie_pas_il_s_annule(lasagna_line, make_user):
    entry = stop(lasagna_line, at(7), at(8))
    with pytest.raises(ValidationError):
        oee.cancel_stop(entry, reason=" ")
    cancelled = oee.cancel_stop(entry, reason="Erreur de ligne", user=make_user("production"))
    assert cancelled.cancelled_by.username == "user-production"
    with pytest.raises(ValidationError):
        oee.cancel_stop(cancelled, reason="encore")
    # Annulé : on peut ressaisir sur la même plage
    stop(lasagna_line, at(7), at(8), StopCategory.STAFF_SHORTAGE)
    assert LineStop.objects.filter(cancelled_at__isnull=True).count() == 1


# --- Calcul --------------------------------------------------------------------------------


@pytest.fixture
def shift(launched, lasagna_line):
    """Plage de 6 h à 11 h (5 h) ; 30 min de nettoyage planifié, 1 h de panne, 30 min de
    changement de série ; 7 200 produits dont 240 rebutés (cadence 2 400 / h)."""
    declare(launched("7200"), "6960", at(6), at(11), scrap="240", reason="Barquettes écrasées")
    stop(lasagna_line, at(6), at(6, 30), StopCategory.PLANNED_CLEANING)
    stop(lasagna_line, at(8), at(9), StopCategory.BREAKDOWN)
    stop(lasagna_line, at(9), at(9, 30), StopCategory.CHANGEOVER)
    return lasagna_line


def test_trs_disponibilite_performance_qualite(shift):
    result = oee.report(YESTERDAY, YESTERDAY)
    line = result["lines"][0]["row"]
    # Requis = 5 − 0,5 = 4,5 h ; fonctionnement = 4,5 − 1,5 = 3 h
    # Net = 7 200 ÷ 2 400 = 3 h ; utile = 6 960 ÷ 2 400 = 2,9 h
    assert (line.opening, line.required, line.operating) == (D("5"), D("4.5"), D("3"))
    rates = result["lines"][0]["rates"]
    assert (rates.availability, rates.performance, rates.quality) == (
        D("66.7"), D("100.0"), D("96.7"),
    )  # fmt: skip
    assert rates.oee == D("64.4")  # 2,9 ÷ 4,5
    assert result["total"].oee == D("64.4")
    # Pareto : arrêts non planifiés seulement dans les parts
    pareto = {row["category"]: row for row in result["pareto"]}
    assert pareto["panne"]["share"] == D("66.7")
    assert pareto["nettoyage_planifie"]["share"] is None


def test_arret_annule_ne_compte_plus(shift):
    breakdown = LineStop.objects.get(category=StopCategory.BREAKDOWN)
    oee.cancel_stop(breakdown, reason="Saisi en double")
    rates = oee.report(YESTERDAY, YESTERDAY)["lines"][0]["rates"]
    assert rates.availability == D("88.9")  # (4,5 − 0,5) ÷ 4,5


def test_la_vue_bi_et_le_tableau_de_bord_donnent_le_meme_trs(shift, factory_site, launched):
    # Un autre jour, avec un arrêt plus long que la marche (jamais de temps négatif)
    other = YESTERDAY - timedelta(days=1)
    declare(launched("2400", other), "2400", at(6, day=other), at(7, day=other))
    stop(shift, at(12, day=other), at(15, day=other))
    start = YESTERDAY - timedelta(days=6)
    expected = oee.report(start, YESTERDAY)
    value, detail = indicators.oee(start, YESTERDAY, None)
    assert value == expected["total"].oee
    assert indicators.oee(start, YESTERDAY, factory_site.pk)[0] == expected["total"].oee
    assert "disponibilité" in detail
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT required_hours, operating_hours FROM bi.fact_line_time WHERE date = %s",
            [other],
        )
        assert cursor.fetchone() == (D("1"), D("0"))


# --- API ---------------------------------------------------------------------------------


def test_api_saisie_d_un_arret_et_rapport(api_client_for, lasagna_line, shift):
    client = api_client_for("production")
    response = client.post(
        "/api/production/line-stops/",
        {
            "line": lasagna_line.pk,
            "started_at": at(10).isoformat(),
            "ended_at": at(10, 10).isoformat(),
            "category": "reglage",
            "comment": "Réglage de l'operculeuse",
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    assert response.json()["minutes"] == 10
    assert api_client_for("commercial").post("/api/production/line-stops/", {}).status_code == 403

    data = client.get(
        "/api/production/oee/", {"start": str(YESTERDAY), "end": str(YESTERDAY)}
    ).json()
    assert data["target"] == "70"
    assert data["lines"][0]["line_code"] == "L1"
    assert data["lines"][0]["required_hours"] == "4.50"
    stops = client.get(
        "/api/production/line-stops/", {"start": str(YESTERDAY), "end": str(YESTERDAY)}
    ).json()
    assert stops["count"] == 4


def test_api_declaration_d_un_produit_fini_exige_la_plage(api_client_for, launched):
    order = launched()
    response = api_client_for("production").post(
        f"/api/production/orders/{order.pk}/declare/",
        {"quantity": "100", "consumptions": []},
        format="json",
    )
    assert response.status_code == 400
    assert "marche" in str(response.json())
