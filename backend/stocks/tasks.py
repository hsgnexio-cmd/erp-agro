"""Tâches de fond Celery du module stocks."""

from celery import shared_task

from .monitoring import run_daily_checks


@shared_task
def daily_checks() -> dict[str, int]:
    """Lancée chaque matin à 6 h par Celery Beat (voir CELERY_BEAT_SCHEDULE)."""
    return run_daily_checks()
