"""Jours ouvrés en production et aux achats (phase 11), sur le vrai calendrier."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from achats import services as purchasing
from previsions.forecast import current_week
from previsions.models import ForecastLine, ForecastVersion
from production import master_plan, orders, planning
from referentiel import calendar
from referentiel.models import Supplier

pytestmark = pytest.mark.calendrier
D = Decimal


def next_week_with_holiday() -> tuple[date, date]:
    """Prochaine semaine à venir (après S+1) dont un jour du lundi au vendredi est férié."""
    week = current_week() + timedelta(days=14)
    for _ in range(80):
        for day in master_plan.work_days(week):
            if calendar.holiday(day):
                return week, day
        week += timedelta(days=7)
    raise AssertionError("aucun jour férié en semaine trouvé")


@pytest.fixture
def plan_with_holiday(lasagna_line, finished_product, private_label_customer, factory):
    week, holiday = next_week_with_holiday()
    version = ForecastVersion.objects.create(
        number="PRV-T-1", created_at=master_plan.week_start_moment(current_week()),
        source="auto", first_week=week,
    )  # fmt: skip
    ForecastLine.objects.create(
        version=version, customer=private_label_customer, article=finished_product,
        week=week, base_quantity=D("7000"), quantity=D("7000"),
    )  # fmt: skip
    plan, _ = master_plan.compute_plan(week, at=master_plan.week_start_moment(current_week()))
    return plan, holiday


def test_le_plan_ne_prevoit_rien_un_jour_ferie(plan_with_holiday, finished_product):
    plan, holiday = plan_with_holiday
    item = plan.items.get(article=finished_product)
    days = {entry.day: entry.quantity for entry in item.days.all()}
    assert days[holiday] == 0
    assert sum(days.values()) == item.proposed_quantity  # réparti sur les 4 autres jours
    assert len([q for q in days.values() if q > 0]) == 4
    with pytest.raises(ValidationError) as exc:
        master_plan.set_quantity(plan, article=finished_product, day=holiday, quantity=D("12"))
    assert "ne fabrique pas" in exc.value.messages[0] and "férié" in exc.value.messages[0]
    load = master_plan.line_load(plan)[0]["cells"]
    assert next(cell for cell in load if cell["day"] == holiday)["closed"].startswith("férié")


def test_planning_signale_un_of_un_jour_non_ouvre(lasagna_line, finished_product, factory):
    saturday = current_week() + timedelta(days=12)
    orders.create_order(
        article=finished_product, planned_quantity=D("2400"), planned_date=saturday,
        line=lasagna_line,
    )  # fmt: skip
    week = planning.week_planning(current_week() + timedelta(days=7))
    cell = next(c for c in week["lines"][0]["cells"] if c["date"] == saturday)
    assert cell["closed"] == "week-end"
    assert cell["warnings"] == ["Jour non ouvré (week-end) : OF à confirmer ou à déplacer."]


def test_delai_fournisseur_en_jours_ouvres(warehouse_site, cream):
    supplier = Supplier.objects.create(
        code="FOU-004", name="Crèmerie", lead_time_days=3, audited=True,
        last_audit_date=date(2026, 3, 1),
    )  # fmt: skip
    from achats.tests.conftest import reference

    reference(supplier, cream)
    friday = date(2026, 11, 13)
    order = purchasing.create_purchase_order(
        supplier=supplier, delivery_site=warehouse_site, order_date=friday,
        lines=[{"article": cream, "quantity": D("100")}],
    )  # fmt: skip
    # Vendredi + 3 jours ouvrés de réception : lundi, mardi, mercredi
    assert order.expected_delivery_date == date(2026, 11, 18)


@pytest.fixture
def warehouse_site(db):
    from referentiel.models import Site

    return Site.objects.create(code="MPE", name="Entrepôt", site_type="entrepot")
