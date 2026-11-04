"""Ordres de fabrication et déclarations de production."""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from simple_history.models import HistoricalRecords

from referentiel.models import Article, Location, ProductionLine, Site
from stocks.models import Lot


class OrderStatus(models.TextChoices):
    PLANNED = "planifie", "Planifié"
    LAUNCHED = "lance", "Lancé"
    DONE = "termine", "Terminé"
    CANCELLED = "annule", "Annulé"


class ProductionOrder(models.Model):
    """Ordre de fabrication (OF) : quoi fabriquer, combien, quand, sur quelle ligne."""

    number = models.CharField("numéro", max_length=20, unique=True)
    article = models.ForeignKey(
        Article, on_delete=models.PROTECT, related_name="production_orders", verbose_name="article"
    )
    planned_quantity = models.DecimalField(
        "quantité prévue",
        max_digits=14,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    planned_date = models.DateField("date prévue")
    sequence = models.PositiveSmallIntegerField(
        "ordre dans la journée", default=1, help_text="1 = premier OF de la journée sur la ligne."
    )
    site = models.ForeignKey(
        Site, on_delete=models.PROTECT, related_name="production_orders", verbose_name="usine"
    )
    line = models.ForeignKey(
        ProductionLine,
        on_delete=models.PROTECT,
        related_name="orders",
        null=True,
        blank=True,
        verbose_name="ligne",
    )
    output_location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="production_orders",
        verbose_name="emplacement de sortie",
    )
    status = models.CharField(
        "statut", max_length=20, choices=OrderStatus.choices, default=OrderStatus.PLANNED
    )
    comment = models.TextField("commentaire", blank=True)
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="production_orders",
        null=True,
        blank=True,
        verbose_name="créé par",
    )
    launched_at = models.DateTimeField("lancé le", null=True, blank=True)
    closed_at = models.DateTimeField("clos le", null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="closed_production_orders",
        null=True,
        blank=True,
        verbose_name="clos par",
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["-planned_date", "line__code", "sequence", "-id"]
        verbose_name = "ordre de fabrication"
        verbose_name_plural = "ordres de fabrication"

    def __str__(self) -> str:
        return f"{self.number} – {self.article.code}"


class ProductionDeclaration(models.Model):
    """Une déclaration de production sur un OF (par exemple une par équipe)."""

    order = models.ForeignKey(
        ProductionOrder,
        on_delete=models.PROTECT,
        related_name="declarations",
        verbose_name="ordre de fabrication",
    )
    lot = models.OneToOneField(
        Lot, on_delete=models.PROTECT, related_name="declaration", verbose_name="lot fabriqué"
    )
    declared_at = models.DateTimeField("déclarée le", auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="production_declarations",
        null=True,
        blank=True,
        verbose_name="déclarée par",
    )
    comment = models.TextField("commentaire", blank=True)
    # Règle 4 : lots consommés hors ordre FEFO, avec leur justification
    fefo_deviations = models.JSONField("écarts au FEFO", default=list, blank=True)

    class Meta:
        ordering = ["declared_at", "id"]
        verbose_name = "déclaration de production"
        verbose_name_plural = "déclarations de production"

    def __str__(self) -> str:
        return f"{self.order.number} → {self.lot.number}"
