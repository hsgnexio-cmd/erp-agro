"""Prévisions de vente : calcul, promotions, corrections, versions figées, fiabilité à S-1."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from previsions import forecast
from previsions.models import ForecastLine, ForecastVersion, Promotion, VersionSource
from previsions.tests.conftest import moment, week
from ventes import orders

D = Decimal


def quantity_for(rows, customer, article, monday):
    for row in rows:
        if row.customer == customer and row.article == article and row.week == monday:
            return row
    return None


# --- Calcul de base -----------------------------------------------------------------------


def test_horizon_de_huit_semaines_a_partir_de_la_semaine_prochaine(db):
    weeks = forecast.horizon()
    assert len(weeks) == 8
    assert weeks[0] == week(1)
    assert weeks[-1] == week(8)
    assert all(monday.weekday() == 0 for monday in weeks)


def test_moyenne_ponderee_des_quatre_dernieres_semaines_arrondie_au_colis(
    private_label_customer, finished_product, place_order
):
    for offset, quantity in ((-1, 1200), (-2, 1000), (-3, 800), (-4, 600)):
        place_order(private_label_customer, finished_product, quantity, week(offset) + timedelta(2))
    rows = forecast.compute()
    row = quantity_for(rows, private_label_customer, finished_product, week(1))
    # (1200×40 + 1000×30 + 800×20 + 600×10) ÷ 100 = 1000 → 996 (83 colis de 12)
    assert row.base_quantity == D("996")
    assert row.quantity == D("996")
    # Même quantité sur les 8 semaines (pas de promotion ni de correction)
    assert {r.quantity for r in rows if r.customer == private_label_customer} == {D("996")}


def test_semaines_avant_la_premiere_commande_ignorees(
    private_label_customer, finished_product, place_order
):
    place_order(private_label_customer, finished_product, 1200, week(-1) + timedelta(1))
    place_order(private_label_customer, finished_product, 600, week(-2) + timedelta(1))
    row = quantity_for(forecast.compute(), private_label_customer, finished_product, week(1))
    # (1200×40 + 600×30) ÷ 70 = 942,9 → 948 ; S-3 et S-4 ne comptent pas pour zéro
    assert row.base_quantity == D("948")


def test_commandes_annulees_et_semaine_en_cours_ignorees(
    private_label_customer, finished_product, place_order
):
    place_order(private_label_customer, finished_product, 1200, week(-1) + timedelta(1))
    cancelled = place_order(private_label_customer, finished_product, 5000, week(-1) + timedelta(2))
    orders.cancel_order(cancelled)
    place_order(private_label_customer, finished_product, 9000, week(1) + timedelta(1))
    row = quantity_for(forecast.compute(), private_label_customer, finished_product, week(1))
    assert row.base_quantity == D("1200")


def test_un_produit_mdd_n_est_prevu_que_pour_son_enseigne(
    private_label_customer, brand_only_customer, mdd_lasagna
):
    pairs = {(c.code, a.code) for c, a in forecast.forecastable_pairs()}
    assert ("ENS2", mdd_lasagna.code) in pairs
    assert ("ENS4", mdd_lasagna.code) not in pairs


# --- Promotions -----------------------------------------------------------------------


def promo(customer, article, first, last=None, coefficient="2", **kwargs):
    return forecast.create_promotion(
        customer=customer,
        article=article,
        first_week=first,
        last_week=last or first,
        coefficient=D(coefficient),
        **kwargs,
    )


def test_promotion_multiplie_la_prevision_de_ses_semaines(
    private_label_customer, finished_product, place_order
):
    place_order(private_label_customer, finished_product, 1200, week(-1) + timedelta(1))
    promotion = promo(private_label_customer, finished_product, week(7), week(8), "2.5")
    rows = forecast.compute()
    normal = quantity_for(rows, private_label_customer, finished_product, week(6))
    boosted = quantity_for(rows, private_label_customer, finished_product, week(7))
    assert normal.quantity == D("1200") and normal.promotion is None
    assert boosted.promotion == promotion
    assert boosted.base_quantity == D("1200")
    assert boosted.quantity == D("3000")
    assert quantity_for(rows, private_label_customer, finished_product, week(8)).quantity == 3000


def test_semaine_passee_en_promotion_ramenee_a_son_volume_normal(
    private_label_customer, finished_product, place_order
):
    # Promotion ×3 en S-1 (saisie il y a longtemps) : 3600 commandés = 1200 « normaux »
    Promotion.objects.create(
        customer=private_label_customer,
        article=finished_product,
        first_week=week(-1),
        last_week=week(-1),
        coefficient=D("3"),
        announced_on=week(-8),
        created_at=moment(week(-8)),
    )
    place_order(private_label_customer, finished_product, 3600, week(-1) + timedelta(1))
    place_order(private_label_customer, finished_product, 1200, week(-2) + timedelta(1))
    row = quantity_for(forecast.compute(), private_label_customer, finished_product, week(1))
    assert row.base_quantity == D("1200")


def test_coefficient_au_dela_de_trois_refuse(private_label_customer, finished_product):
    with pytest.raises(ValidationError) as exc:
        promo(private_label_customer, finished_product, week(7), coefficient="3.5")
    assert "×3" in str(exc.value)


def test_promotion_commencant_cette_semaine_refusee(private_label_customer, finished_product):
    with pytest.raises(ValidationError) as exc:
        promo(private_label_customer, finished_product, week(0))
    assert "semaine prochaine" in exc.value.messages[0]


def test_deux_promotions_qui_se_chevauchent_refusees(private_label_customer, finished_product):
    promo(private_label_customer, finished_product, week(6), week(7))
    with pytest.raises(ValidationError) as exc:
        promo(private_label_customer, finished_product, week(7), week(8))
    assert "déjà prévue" in exc.value.messages[0]


def test_promotion_mdd_refusee_pour_une_autre_enseigne(brand_only_customer, mdd_lasagna):
    with pytest.raises(ValidationError) as exc:
        promo(brand_only_customer, mdd_lasagna, week(7))
    assert "MDD de ENS2" in str(exc.value)


def test_promotion_annoncee_tard_acceptee(private_label_customer, finished_product):
    promotion = promo(private_label_customer, finished_product, week(2))
    assert promotion.notice_days < forecast.MIN_NOTICE_DAYS  # simple avertissement


def test_promotion_annulee_ne_compte_plus_et_motif_obligatoire(
    private_label_customer, finished_product, place_order, make_user
):
    place_order(private_label_customer, finished_product, 1200, week(-1) + timedelta(1))
    promotion = promo(private_label_customer, finished_product, week(7))
    with pytest.raises(ValidationError):
        forecast.cancel_promotion(promotion, reason=" ")
    forecast.cancel_promotion(promotion, reason="Enseigne a renoncé", user=make_user("commercial"))
    row = quantity_for(forecast.compute(), private_label_customer, finished_product, week(7))
    assert row.promotion is None and row.quantity == D("1200")
    # Une nouvelle promotion peut alors être saisie sur la même semaine
    promo(private_label_customer, finished_product, week(7), coefficient="1.5")


# --- Corrections manuelles -------------------------------------------------------------


def correct(customer, article, monday, quantity, reason="Référencement dans 20 magasins"):
    return forecast.create_adjustment(
        customer=customer,
        article=article,
        week=monday,
        quantity=None if quantity is None else D(quantity),
        reason=reason,
    )


def test_correction_remplace_la_quantite_calculee_et_la_derniere_l_emporte(
    private_label_customer, finished_product, place_order
):
    place_order(private_label_customer, finished_product, 1200, week(-1) + timedelta(1))
    promo(private_label_customer, finished_product, week(3))
    correct(private_label_customer, finished_product, week(3), "2000")
    latest = correct(private_label_customer, finished_product, week(3), "2400")
    row = quantity_for(forecast.compute(), private_label_customer, finished_product, week(3))
    assert row.adjustment == latest
    assert row.promo_quantity == D("2400")  # le détail reste visible
    assert row.quantity == D("2400")


def test_correction_vide_rend_la_main_au_calcul(
    private_label_customer, finished_product, place_order
):
    place_order(private_label_customer, finished_product, 1200, week(-1) + timedelta(1))
    correct(private_label_customer, finished_product, week(2), "0")
    assert quantity_for(
        forecast.compute(), private_label_customer, finished_product, week(2)
    ).quantity == D("0")
    correct(private_label_customer, finished_product, week(2), None, "Retour au calcul")
    row = quantity_for(forecast.compute(), private_label_customer, finished_product, week(2))
    assert row.adjustment is None and row.quantity == D("1200")


def test_correction_sur_un_produit_sans_historique(private_label_customer, finished_product):
    correct(private_label_customer, finished_product, week(4), "600", "Lancement en magasin")
    row = quantity_for(forecast.compute(), private_label_customer, finished_product, week(4))
    assert row.base_quantity == D("0") and row.quantity == D("600")


def test_correction_hors_horizon_ou_sans_motif_refusee(private_label_customer, finished_product):
    with pytest.raises(ValidationError) as exc:
        correct(private_label_customer, finished_product, week(0), "100")
    assert "S+1 à S+8" in exc.value.messages[0]
    with pytest.raises(ValidationError) as exc:
        correct(private_label_customer, finished_product, week(9), "100")
    with pytest.raises(ValidationError) as exc:
        correct(private_label_customer, finished_product, week(2), "100", reason="  ")
    assert "motif" in str(exc.value)


def test_correction_jamais_modifiee_ni_supprimee(private_label_customer, finished_product):
    adjustment = correct(private_label_customer, finished_product, week(2), "100")
    adjustment.quantity = D("200")
    with pytest.raises(ValidationError):
        adjustment.save()
    with pytest.raises(ValidationError):
        adjustment.delete()


# --- Versions figées ------------------------------------------------------------------


def test_version_figee_avec_son_detail_et_jamais_modifiee(
    private_label_customer, finished_product, place_order, make_user
):
    place_order(private_label_customer, finished_product, 1200, week(-1) + timedelta(1))
    promo(private_label_customer, finished_product, week(5))
    version = forecast.create_version(user=make_user("commercial"), comment="Avant réunion S&OP")
    assert version.number.startswith(f"PRV-{timezone.localdate().year}-")
    assert version.first_week == week(1)
    assert version.lines.count() == 8
    line = version.lines.get(week=week(5))
    assert (line.base_quantity, line.promo_coefficient, line.quantity) == (
        D("1200"), D("2.00"), D("2400"),
    )  # fmt: skip
    with pytest.raises(ValidationError):
        version.save()
    with pytest.raises(ValidationError):
        ForecastLine.objects.filter(version=version).update(quantity=0)
    with pytest.raises(ValidationError):
        ForecastLine.objects.filter(version=version).delete()


def test_version_du_lundi_figee_une_seule_fois_par_jour(db):
    at = moment(week(0))
    first = forecast.freeze_weekly(at)
    assert first.source == VersionSource.AUTOMATIC
    assert forecast.freeze_weekly(at + timedelta(hours=2)) is None
    assert ForecastVersion.objects.count() == 1


def test_une_version_passee_ignore_les_corrections_saisies_apres(
    private_label_customer, finished_product, place_order
):
    place_order(private_label_customer, finished_product, 1200, week(-1) + timedelta(1))
    correct(private_label_customer, finished_product, week(2), "60")
    version = forecast.create_version(at=timezone.now() - timedelta(minutes=5))
    assert version.lines.get(week=week(2)).quantity == D("1200")


# --- Fiabilité à S-1 ------------------------------------------------------------------


@pytest.fixture
def measured_week(private_label_customer, brand_only_customer, finished_product, place_order):
    """Semaine dernière (S-1) : prévision figée le lundi de S-2, puis commandes réelles."""
    target = week(-1)
    place_order(private_label_customer, finished_product, 1200, week(-3) + timedelta(1))
    version = forecast.create_version(source=VersionSource.AUTOMATIC, at=moment(week(-2)))
    # Réel : 1000 pour ENS2 (prévu 1200), 120 pour ENS4 (rien de prévu)
    place_order(private_label_customer, finished_product, 1000, target + timedelta(2))
    place_order(brand_only_customer, finished_product, 120, target + timedelta(3))
    return target, version


def test_fiabilite_a_s1_ecart_absolu_sur_ventes_reelles(measured_week, private_label_customer):
    target, version = measured_week
    result = forecast.week_accuracy(target)
    assert result.version == version and result.complete
    assert (result.forecast, result.actual, result.abs_error) == (D("1200"), D("1120"), D("320"))
    # 1 − 320 ÷ 1120 = 71,4 %
    assert result.accuracy == D("71.4")
    # Par enseigne : ENS2 seule, 1 − 200 ÷ 1000
    assert forecast.week_accuracy(target, private_label_customer.pk).accuracy == D("80.0")


def test_une_version_figee_pendant_la_semaine_ne_compte_pas(measured_week):
    target, version = measured_week
    forecast.create_version(at=moment(target, 6))  # figée le lundi même : trop tard
    assert forecast.week_accuracy(target).version == version


def test_fiabilite_jamais_negative_et_semaine_en_cours_non_terminee(
    private_label_customer, finished_product, place_order
):
    place_order(private_label_customer, finished_product, 1200, week(-2) + timedelta(1))
    forecast.create_version(at=moment(week(-1)))
    place_order(private_label_customer, finished_product, 120, week(0) + timedelta(1))
    result = forecast.week_accuracy(week(0))
    assert result.accuracy == D("0.0")  # 1 − 1080 ÷ 120 < 0
    assert result.complete is False
    assert forecast.overall_accuracy([result]) is None


def test_semaine_sans_version_s1_non_mesuree(private_label_customer, finished_product, place_order):
    place_order(private_label_customer, finished_product, 1200, week(-1) + timedelta(1))
    assert forecast.week_accuracy(week(-1)) is None
    assert forecast.accuracy_by_week(week(-4), timezone.localdate()) == []
