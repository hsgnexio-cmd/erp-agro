"""Prévisions de démonstration (phase 9a) : promotions à venir et une correction manuelle.

Les versions figées des semaines passées et la promotion déjà réalisée sont créées par
l'historique de démonstration (pilotage/demo_history.py), qui rejoue les commandes.
"""

from datetime import timedelta
from decimal import Decimal

from django.db import transaction

from referentiel.models import Article, Customer

from . import forecast
from .models import Promotion

COMMENT = "Démonstration"

# (enseigne, produit, semaines après la semaine courante, durée en semaines, coefficient)
FUTURE_PROMOTIONS = [
    # Annoncée dans les délais habituels (7 semaines avant)
    ("ENS1", "PF-PAT-LASBOL-ENS1-300", 7, 2, Decimal("1.8")),
    # Annoncée tard (3 semaines avant) : acceptée, mais signalée
    ("ENS3", "PF-GRA-HACHIS-BRE-300", 3, 1, Decimal("1.5")),
]
# Correction manuelle : (enseigne, produit, semaine S+n, quantité, motif)
ADJUSTMENT = (
    "ENS2", "PF-ENT-CELREM-ENS2-250", 2, Decimal("1800"),
    "Fin de référencement dans 15 magasins Marché Plus",
)  # fmt: skip


@transaction.atomic
def load_demo_data() -> dict[str, int | str]:
    if Promotion.objects.filter(comment=COMMENT, first_week__gte=forecast.current_week()).exists():
        return {"prévisions": "déjà présentes, non modifiées"}
    articles = {article.code: article for article in Article.objects.filter(active=True)}
    customers = {customer.code: customer for customer in Customer.objects.all()}
    this_week = forecast.current_week()
    created = 0
    for customer, code, offset, weeks, coefficient in FUTURE_PROMOTIONS:
        first = this_week + timedelta(days=7 * offset)
        forecast.create_promotion(
            customer=customers[customer],
            article=articles[code],
            first_week=first,
            last_week=first + timedelta(days=7 * (weeks - 1)),
            coefficient=coefficient,
            comment=COMMENT,
        )
        created += 1
    customer, code, offset, quantity, reason = ADJUSTMENT
    forecast.create_adjustment(
        customer=customers[customer],
        article=articles[code],
        week=this_week + timedelta(days=7 * offset),
        quantity=quantity,
        reason=reason,
    )
    return {"promotions à venir": created, "corrections manuelles": 1}
