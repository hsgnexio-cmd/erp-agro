"""Tâches de fond Celery du module ventes."""

from celery import shared_task

from .edi import simulate_day


@shared_task
def simulate_edi_orders() -> dict[str, int]:
    """Simule la réception des commandes EDI des enseignes (chaque jour de semaine à 9 h 30)."""
    messages = simulate_day()
    integrated = sum(1 for message in messages if message.status == "integre")
    return {
        "messages": len(messages),
        "intégrés": integrated,
        "rejetés": len(messages) - integrated,
    }
