"""Tâches de fond Celery du module prévisions."""

from celery import shared_task

from .forecast import freeze_weekly


@shared_task
def freeze_weekly_forecast() -> str:
    """Fige la prévision à 8 semaines (chaque lundi à 5 h)."""
    version = freeze_weekly()
    return version.number if version else "version du jour déjà figée"
