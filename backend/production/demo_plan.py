"""Plan de production de démonstration (phase 9b) : plan de la semaine prochaine, en brouillon.

Chargé après l'historique, pour s'appuyer sur ses prévisions figées et son stock. Il n'est pas
figé : la production peut l'ajuster puis le figer (sinon, gel automatique samedi à 12 h).
Aucun plan n'est rejoué dans l'historique : ses OF « planifiés » resteraient dans le passé.
"""

from datetime import timedelta

from previsions.forecast import current_week

from . import master_plan
from .models import MasterPlan


def load_demo_data() -> dict[str, int | str]:
    week = current_week() + timedelta(days=7)
    if MasterPlan.objects.filter(week=week).exists():
        return {"plan de production": "déjà présent, non modifié"}
    plan, skipped = master_plan.compute_plan(week)
    return {"produits planifiés (brouillon)": plan.items.count(), "produits écartés": len(skipped)}
