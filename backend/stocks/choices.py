from django.db import models


class LotStatus(models.TextChoices):
    """Règle 6 : seul un lot libéré peut être consommé ou expédié."""

    RELEASED = "libere", "Libéré"
    BLOCKED = "bloque", "Bloqué"
    QUARANTINE = "quarantaine", "Quarantaine"
    DESTROYED = "detruit", "Détruit"


class MovementType(models.TextChoices):
    RECEPTION = "reception", "Réception fournisseur"
