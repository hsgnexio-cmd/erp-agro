"""Ordres de fabrication, déclarations de production et plan de production (phase 9b)."""

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


# --- Plan de production hebdomadaire (phase 9b) ------------------------------------------

QUANTITY = {"max_digits": 14, "decimal_places": 3}


class PlanStatus(models.TextChoices):
    DRAFT = "brouillon", "Brouillon"
    FROZEN = "fige", "Figé"


class MasterPlan(models.Model):
    """Plan de production d'une semaine (produits finis), figé à J-2 (le samedi).

    Le gel crée les ordres de fabrication ; un plan figé ne se modifie plus.
    """

    week = models.DateField("semaine (lundi)", unique=True)
    status = models.CharField(
        "statut", max_length=10, choices=PlanStatus.choices, default=PlanStatus.DRAFT
    )
    forecast_version = models.ForeignKey(
        "previsions.ForecastVersion",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="master_plans",
        verbose_name="version de prévision utilisée",
        help_text="Vide = prévision du moment (aucune version figée ne couvrait la semaine).",
    )
    computed_at = models.DateTimeField("calculé le")
    computed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="computed_master_plans",
        null=True,
        blank=True,
        verbose_name="calculé par",
    )
    frozen_at = models.DateTimeField("figé le", null=True, blank=True)
    frozen_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="frozen_master_plans",
        null=True,
        blank=True,
        verbose_name="figé par",
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["-week"]
        verbose_name = "plan de production"
        verbose_name_plural = "plans de production"

    def __str__(self) -> str:
        return f"Plan de la semaine du {self.week:%d/%m/%Y} ({self.get_status_display()})"


class MasterPlanItem(models.Model):
    """Un produit fini du plan : détail du calcul et ligne de conditionnement retenue."""

    plan = models.ForeignKey(
        MasterPlan, on_delete=models.CASCADE, related_name="items", verbose_name="plan"
    )
    article = models.ForeignKey(
        Article, on_delete=models.PROTECT, related_name="master_plan_items", verbose_name="produit"
    )
    line = models.ForeignKey(
        ProductionLine,
        on_delete=models.PROTECT,
        related_name="master_plan_items",
        verbose_name="ligne",
    )
    forecast_quantity = models.DecimalField("prévision de la semaine", **QUANTITY)
    ordered_quantity = models.DecimalField("commandes déjà reçues", **QUANTITY)
    demand = models.DecimalField("demande retenue", **QUANTITY)
    safety_days = models.DecimalField("stock de sécurité (jours)", max_digits=4, decimal_places=1)
    safety_stock = models.DecimalField("stock de sécurité", **QUANTITY)
    stock = models.DecimalField("stock disponible au calcul", **QUANTITY)
    open_orders = models.DecimalField("OF à venir avant la semaine", **QUANTITY)
    demand_before = models.DecimalField("demande prévue d'ici la semaine", **QUANTITY)
    projected_stock = models.DecimalField("stock projeté au lundi", **QUANTITY)
    proposed_quantity = models.DecimalField("quantité calculée", **QUANTITY)
    history = HistoricalRecords()

    class Meta:
        ordering = ["plan", "line__code", "article__code"]
        verbose_name = "produit du plan"
        verbose_name_plural = "produits du plan"
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "article"], name="unique_article_per_master_plan"
            )
        ]

    def __str__(self) -> str:
        return f"{self.article.code} ({self.line.code})"


class MasterPlanDay(models.Model):
    """Quantité à fabriquer un jour donné ; l'OF est créé au gel du plan."""

    item = models.ForeignKey(
        MasterPlanItem, on_delete=models.CASCADE, related_name="days", verbose_name="produit"
    )
    day = models.DateField("jour")
    quantity = models.DecimalField(
        "quantité à fabriquer", **QUANTITY, validators=[MinValueValidator(Decimal("0"))]
    )
    production_order = models.OneToOneField(
        ProductionOrder,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="master_plan_day",
        verbose_name="OF créé au gel",
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["item", "day"]
        verbose_name = "jour du plan"
        verbose_name_plural = "jours du plan"
        constraints = [
            models.UniqueConstraint(fields=["item", "day"], name="unique_day_per_plan_item")
        ]

    def __str__(self) -> str:
        return f"{self.item.article.code} – {self.day} : {self.quantity}"
