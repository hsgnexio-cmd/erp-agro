"""Historique de démonstration (phase 8) : rejoué avec toutes les règles métier."""

import pytest
from django.core.management import call_command
from django.utils import timezone

from pilotage import demo_history
from production.models import ProductionOrder
from stocks.models import StockMovement
from ventes.models import CustomerOrder, Shipment


@pytest.fixture
def demo(db):
    call_command("charger_donnees_demo", sans_historique=True)


def test_historique_rejoue_les_journees_passees_avec_leurs_dates(demo):
    counts = demo_history.load_demo_data(days=4)
    assert counts["OF"] > 0 and counts["commandes clients"] > 0

    today = timezone.localdate()
    history = CustomerOrder.objects.filter(customer_reference__startswith="HIST-")
    assert history.exists()
    # Chaque mouvement porte la date de sa journée, jamais dans le futur
    shipped = StockMovement.objects.filter(
        reference__in=Shipment.objects.filter(order__in=history).values("number")
    )
    assert shipped.exists()
    assert all(timezone.localdate(m.created_at) < today for m in shipped)
    assert ProductionOrder.objects.filter(
        comment="", planned_date__lt=today, status="termine"
    ).exists()

    # Relancer ne crée aucun doublon
    assert demo_history.load_demo_data(days=4) == {"historique": "déjà présent, non modifié"}
