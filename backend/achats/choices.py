from django.db import models


class PurchaseOrderStatus(models.TextChoices):
    DRAFT = "brouillon", "Brouillon"
    SENT = "envoyee", "Envoyée"
    PARTIAL = "partiellement_recue", "Partiellement reçue"
    CLOSED = "soldee", "Soldée"
    CANCELLED = "annulee", "Annulée"
