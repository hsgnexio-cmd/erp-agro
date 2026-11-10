"""Calendrier (phase 11) : jours fériés, fermetures de site, jours ouvrés, heure limite."""

from datetime import date, datetime, time

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from referentiel import calendar
from referentiel.calendar import Activity
from referentiel.choices import SiteType
from referentiel.models import Site, SiteClosure
from ventes import orders

pytestmark = pytest.mark.calendrier

# Semaine de référence : mardi 10/11/2026, mercredi 11/11 férié (Armistice)
TUESDAY, ARMISTICE, THURSDAY, FRIDAY = (date(2026, 11, d) for d in (10, 11, 12, 13))
SATURDAY, SUNDAY, MONDAY = date(2026, 11, 14), date(2026, 11, 15), date(2026, 11, 16)


def at(day: date, hour: int, minute: int = 0) -> datetime:
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


def test_les_onze_jours_feries_et_paques():
    holidays = calendar.french_holidays(2026)
    assert len(holidays) == 11
    assert calendar.easter(2026) == date(2026, 4, 5)
    assert calendar.easter(2027) == date(2027, 3, 28)
    assert holidays[date(2026, 4, 6)] == "Lundi de Pâques"
    assert holidays[date(2026, 5, 14)] == "Ascension"
    assert holidays[date(2026, 5, 25)] == "Lundi de Pentecôte"
    assert holidays[ARMISTICE] == "Armistice 1918"


def test_qui_travaille_quand(db):
    # Usines du lundi au vendredi ; expéditions et livraisons du lundi au samedi
    assert calendar.is_open(FRIDAY, Activity.PRODUCTION, "NAN")
    assert not calendar.is_open(SATURDAY, Activity.PRODUCTION, "NAN")
    assert calendar.is_open(SATURDAY, Activity.SHIPPING)
    assert not calendar.is_open(SUNDAY, Activity.SHIPPING)
    assert not calendar.is_open(SATURDAY, Activity.RECEIVING)
    assert calendar.closed_reason(ARMISTICE, Activity.SHIPPING) == "férié (Armistice 1918)"
    assert calendar.closed_reason(SUNDAY, Activity.SHIPPING) == "dimanche"


def test_jours_ouvres_suivants_et_precedents(db):
    assert calendar.next_open_day(TUESDAY, Activity.PRODUCTION, "NAN", strict=True) == THURSDAY
    assert calendar.previous_open_day(MONDAY, Activity.SHIPPING, strict=True) == SATURDAY
    # 3 jours ouvrés de réception après le mardi : jeudi, vendredi, lundi
    assert calendar.add_open_days(TUESDAY, 3, Activity.RECEIVING) == MONDAY
    assert calendar.add_open_days(MONDAY, -3, Activity.RECEIVING) == TUESDAY
    assert calendar.open_days(MONDAY.replace(day=9), FRIDAY, Activity.PRODUCTION, "NAN") == [
        date(2026, 11, 9), TUESDAY, THURSDAY, FRIDAY,
    ]  # fmt: skip


def test_fermeture_exceptionnelle_d_un_site(db):
    site = Site.objects.create(code="NAN", name="Usine", site_type=SiteType.FACTORY)
    SiteClosure.objects.create(site=site, start_date=THURSDAY, end_date=FRIDAY, reason="Pont")
    assert calendar.closed_reason(FRIDAY, Activity.PRODUCTION, "NAN") == "fermeture NAN (Pont)"
    assert calendar.is_open(FRIDAY, Activity.PRODUCTION, "REN")
    with pytest.raises(ValidationError):
        SiteClosure.objects.create(site=site, start_date=FRIDAY, end_date=MONDAY, reason="Autre")
    with pytest.raises(ValidationError):
        SiteClosure.objects.create(site=site, start_date=MONDAY, end_date=FRIDAY, reason="X")
    with pytest.raises(ValidationError):
        SiteClosure(site=site, start_date=MONDAY, end_date=MONDAY, reason=" ").save()


# --- Heure limite en jours ouvrés ----------------------------------------------------------


@pytest.mark.parametrize(
    ("received", "expected"),
    [
        (at(TUESDAY, 10, 59), THURSDAY),  # le mercredi est férié
        (at(TUESDAY, 11, 0), FRIDAY),
        (at(FRIDAY, 10), SATURDAY),  # les enseignes sont livrées le samedi
        (at(SATURDAY, 10), MONDAY),
        (at(SATURDAY, 12), date(2026, 11, 17)),
        (at(SUNDAY, 18), date(2026, 11, 17)),  # reçue le dimanche = lundi matin
        (at(ARMISTICE, 9), FRIDAY),  # reçue un jour férié = jeudi matin
    ],
)
def test_heure_limite_en_jours_ouvres(db, received, expected):
    assert orders.earliest_delivery_date(received) == expected


def test_a_expedier_au_plus_tard_le_jour_d_expedition_precedent(db):
    assert orders.ship_by_date(MONDAY) == SATURDAY
    assert orders.ship_by_date(THURSDAY) == TUESDAY
    assert orders.delivery_refusal(FRIDAY) is None
    refusal = orders.delivery_refusal(SUNDAY)
    assert refusal == (
        "Pas de livraison le dimanche 15/11/2026 (dimanche) : prochaine date possible le "
        "lundi 16/11/2026."
    )
    assert "férié (Armistice 1918)" in orders.delivery_refusal(ARMISTICE)


def test_commande_refusee_pour_une_livraison_un_jour_ferie(
    private_label_customer, finished_product
):
    from referentiel.models import CustomerWarehouse

    warehouse = CustomerWarehouse.objects.create(
        customer=private_label_customer, code="ENS2-E01", name="Entrepôt", city="Nantes"
    )
    line = [{"article": finished_product, "quantity": 120}]
    with pytest.raises(ValidationError) as exc:
        orders.create_order(
            customer=private_label_customer, warehouse=warehouse,
            requested_delivery_date=ARMISTICE, lines=line, received_at=at(date(2026, 11, 9), 9),
        )  # fmt: skip
    assert "prochaine date possible le jeudi 12/11/2026" in exc.value.messages[0]
    order = orders.create_order(
        customer=private_label_customer, warehouse=warehouse,
        requested_delivery_date=MONDAY, lines=line, received_at=at(FRIDAY, 9),
    )  # fmt: skip
    assert order.ship_by_date == SATURDAY
