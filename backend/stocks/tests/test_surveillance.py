"""Relevés de température (règle 7) et alertes quotidiennes."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from referentiel.choices import TemperatureClass
from stocks import monitoring, services
from stocks.choices import AlertType, LotStatus
from stocks.models import Alert
from stocks.tests.conftest import make_location

# --- Relevés de température ------------------------------------------------------


def test_un_releve_conforme_ne_bloque_rien(make_lot, cream, quarantine):
    lot = services.release_lot(make_lot(cream))
    result = monitoring.record_temperature(quarantine, Decimal("3.5"))

    assert result.reading.is_compliant
    assert (result.reading.min_allowed, result.reading.max_allowed) == (Decimal("0"), Decimal("4"))
    lot.refresh_from_db()
    assert lot.status == LotStatus.RELEASED
    assert Alert.objects.count() == 0


def test_un_ecart_bloque_les_lots_presents_et_cree_une_alerte(
    make_lot, cream, quarantine, make_user
):
    released = services.release_lot(make_lot(cream))
    in_quarantine = make_lot(cream)
    already_blocked = services.block_lot(make_lot(cream), reason="Analyse en cours")

    result = monitoring.record_temperature(quarantine, Decimal("7.2"), user=make_user("magasinier"))

    assert not result.reading.is_compliant
    assert {lot.pk for lot in result.blocked_lots} == {released.pk, in_quarantine.pk}
    released.refresh_from_db()
    assert released.status == LotStatus.BLOCKED
    assert "7,2 °C en MPE-QUAR (limites 0 à 4 °C)" in released.block_reason
    already_blocked.refresh_from_db()
    assert already_blocked.block_reason == "Analyse en cours"  # motif d'origine conservé

    alert = result.alert
    assert alert.alert_type == AlertType.TEMPERATURE
    assert alert.level == "critique"
    assert released.number in alert.message


def test_limites_de_l_emplacement_prioritaires(warehouse):
    room = make_location(warehouse, "MPE-FP-02")
    room.min_temperature, room.max_temperature = Decimal("1"), Decimal("3")
    room.save()
    assert not monitoring.record_temperature(room, Decimal("3.5")).reading.is_compliant


def test_surgele_limite_par_defaut(warehouse):
    frozen = make_location(warehouse, "MPE-FN-02", TemperatureClass.FROZEN)
    assert monitoring.record_temperature(frozen, Decimal("-25")).reading.is_compliant
    assert not monitoring.record_temperature(frozen, Decimal("-15")).reading.is_compliant


def test_un_releve_ne_se_modifie_pas(quarantine):
    reading = monitoring.record_temperature(quarantine, Decimal("3")).reading
    reading.temperature = Decimal("2")
    with pytest.raises(ValidationError):
        reading.save()
    with pytest.raises(ValidationError):
        reading.delete()


def test_pas_de_releve_dans_le_futur(quarantine):
    with pytest.raises(ValidationError):
        monitoring.record_temperature(
            quarantine, Decimal("3"), measured_at=timezone.now() + timedelta(hours=2)
        )


# --- Vérifications quotidiennes ------------------------------------------------------


def test_peremption_proche(make_lot, cream):
    lot = services.release_lot(make_lot(cream, expiry_in=2))
    make_lot(cream, expiry_in=10)  # trop loin : pas d'alerte

    counts = monitoring.run_daily_checks()

    assert counts["péremption proche"] == 1
    alert = Alert.objects.get(alert_type=AlertType.EXPIRY_SOON)
    assert alert.lot == lot
    assert "dans 2 jour(s)" in alert.message


def test_ddm_alerte_30_jours_avant(make_lot, flour, ambient_store):
    make_lot(flour, expiry_in=25, location=ambient_store)
    assert monitoring.run_daily_checks()["péremption proche"] == 1


def test_une_dlc_depassee_bloque_le_lot(make_lot, cream):
    lot = services.release_lot(make_lot(cream, expiry_in=1))
    tomorrow_plus_one = timezone.localdate() + timedelta(days=2)

    counts = monitoring.run_daily_checks(today=tomorrow_plus_one)

    assert counts["DLC dépassée (lots bloqués)"] == 1
    lot.refresh_from_db()
    assert lot.status == LotStatus.BLOCKED
    assert "DLC dépassée" in lot.block_reason


def test_une_ddm_depassee_alerte_sans_bloquer(make_lot, flour, ambient_store):
    lot = services.release_lot(make_lot(flour, expiry_in=1, location=ambient_store))
    counts = monitoring.run_daily_checks(today=timezone.localdate() + timedelta(days=2))

    assert counts["DDM dépassée"] == 1
    lot.refresh_from_db()
    assert lot.status == LotStatus.RELEASED


def test_pas_de_doublon_d_alerte(make_lot, cream):
    make_lot(cream, expiry_in=1)
    monitoring.run_daily_checks()
    monitoring.run_daily_checks()
    assert Alert.objects.filter(alert_type=AlertType.EXPIRY_SOON).count() == 1


def test_releve_manquant_seulement_si_du_stock_est_present(make_lot, cream, quarantine, cold_room):
    make_lot(cream)  # du stock en quarantaine, aucun relevé ; la chambre froide est vide
    counts = monitoring.run_daily_checks()
    assert counts["relevé manquant"] == 1
    assert Alert.objects.get(alert_type=AlertType.MISSING_READING).location == quarantine

    # Après un relevé, plus d'alerte « relevé manquant » nouvelle
    monitoring.record_temperature(quarantine, Decimal("3"))
    Alert.objects.update(resolved_at=timezone.now())
    assert monitoring.run_daily_checks()["relevé manquant"] == 0


def test_traiter_une_alerte(make_lot, cream, make_user):
    make_lot(cream, expiry_in=1)
    monitoring.run_daily_checks()
    alert = Alert.objects.get(alert_type=AlertType.EXPIRY_SOON)

    with pytest.raises(ValidationError):
        monitoring.resolve_alert(alert, user=make_user("qualite"), comment="")
    alert = monitoring.resolve_alert(alert, user=make_user("magasinier"), comment="Lot utilisé")
    assert not alert.is_open
    with pytest.raises(ValidationError):
        alert.delete()


def test_la_tache_celery_est_planifiee_chaque_matin():
    from django.conf import settings

    schedule = settings.CELERY_BEAT_SCHEDULE["verifications-stocks-quotidiennes"]
    assert schedule["task"] == "stocks.tasks.daily_checks"
    assert schedule["schedule"].hour == {6}
