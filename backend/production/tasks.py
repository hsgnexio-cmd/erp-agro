"""Tâches de fond Celery du module production."""

from celery import shared_task

from .master_plan import freeze_next_week


@shared_task
def freeze_next_week_plan() -> str:
    """Fige le plan de production de la semaine prochaine (samedi 12 h, J-2)."""
    plan = freeze_next_week()
    return f"Plan du {plan.week:%d/%m/%Y} figé" if plan else "plan déjà figé"
