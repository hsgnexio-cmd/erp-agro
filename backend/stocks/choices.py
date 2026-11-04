from django.db import models


class LotStatus(models.TextChoices):
    """Règle 6 : seul un lot libéré peut être consommé ou expédié."""

    RELEASED = "libere", "Libéré"
    BLOCKED = "bloque", "Bloqué"
    QUARANTINE = "quarantaine", "Quarantaine"
    DESTROYED = "detruit", "Détruit"


class MovementType(models.TextChoices):
    RECEPTION = "reception", "Réception fournisseur"
    TRANSFER_OUT = "transfert_sortie", "Transfert (sortie)"
    TRANSFER_IN = "transfert_entree", "Transfert (entrée)"
    CORRECTION = "correction", "Correction"
    DESTRUCTION = "destruction", "Destruction"
    INVENTORY = "inventaire", "Ajustement d'inventaire"
    PRODUCTION = "fabrication", "Entrée de fabrication"
    CONSUMPTION = "consommation", "Consommation en fabrication"
    SHIPMENT = "expedition", "Expédition client"
    # Sorties d'invendables (produits finis bloqués ou périmés)
    DONATION = "don", "Don à une association (invendable)"
    ANIMAL_FEED = "alimentation_animale", "Alimentation animale (invendable)"
    UNSOLD_DESTRUCTION = "destruction_invendable", "Destruction (invendable)"


class UnsoldDestination(models.TextChoices):
    """Destination d'un invendable : chacune a son type de mouvement de sortie."""

    DONATION = "don", "Don à une association"
    ANIMAL_FEED = "alimentation_animale", "Alimentation animale"
    DESTRUCTION = "destruction", "Destruction"


class InventoryStatus(models.TextChoices):
    OPEN = "en_cours", "En cours"
    VALIDATED = "valide", "Validé"
    CANCELLED = "annule", "Annulé"


class AlertType(models.TextChoices):
    EXPIRY_SOON = "peremption_proche", "Péremption proche"
    DLC_PASSED = "dlc_depassee", "DLC dépassée"
    DDM_PASSED = "ddm_depassee", "DDM dépassée"
    TEMPERATURE = "ecart_temperature", "Écart de température"
    MISSING_READING = "releve_manquant", "Relevé de température manquant"
    LOW_YIELD = "rendement_faible", "Rendement matière faible"
    SHIPPING_TEMPERATURE = "temperature_expedition", "Température à l'expédition"


class AlertLevel(models.TextChoices):
    WARNING = "attention", "Attention"
    CRITICAL = "critique", "Critique"
