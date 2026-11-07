"""Données de démonstration des prévisions : promotions à venir et correction manuelle."""

import pytest
from django.core.management import call_command

from previsions import demo_data, forecast
from previsions.models import ForecastAdjustment, Promotion


@pytest.fixture
def demo(db):
    call_command("charger_donnees_demo", sans_historique=True)


def test_demo_promotions_a_venir_et_correction(demo):
    promotions = Promotion.objects.filter(comment=demo_data.COMMENT).order_by("first_week")
    assert promotions.count() == 2
    late, on_time = promotions
    assert late.notice_days < forecast.MIN_NOTICE_DAYS <= on_time.notice_days
    assert on_time.last_week > on_time.first_week  # deux semaines
    assert ForecastAdjustment.objects.count() == 1

    # La prévision du moment tient compte de la correction (sans historique, les produits en
    # promotion n'ont pas encore de commandes passées : leur prévision est nulle)
    assert any(row.adjustment is not None for row in forecast.compute())

    # Relancer ne crée aucun doublon
    assert demo_data.load_demo_data() == {"prévisions": "déjà présentes, non modifiées"}
