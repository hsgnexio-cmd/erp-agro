"""Prévisions de vente (phase 9a) : promotions, corrections manuelles, versions figées.

Une prévision se calcule par produit fini × enseigne × semaine (du lundi au dimanche, date
de livraison demandée). Chaque semaine est représentée par la date de son lundi.
"""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from referentiel.models import Article, Customer, ValidatedModel

QUANTITY = {"max_digits": 12, "decimal_places": 3}


class Promotion(ValidatedModel):
    """Promotion annoncée par une enseigne : la demande est multipliée par un coefficient."""

    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="promotions", verbose_name="enseigne"
    )
    article = models.ForeignKey(
        Article, on_delete=models.PROTECT, related_name="promotions", verbose_name="produit fini"
    )
    first_week = models.DateField("première semaine (lundi)")
    last_week = models.DateField("dernière semaine (lundi)")
    # Fiche entreprise : jusqu'à ×3 en volume
    coefficient = models.DecimalField(
        "coefficient de volume",
        max_digits=4,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("1.01"), "Le coefficient doit être supérieur à 1."),
            MaxValueValidator(Decimal("3"), "Le coefficient ne peut pas dépasser ×3."),
        ],
    )
    announced_on = models.DateField("annoncée le")
    comment = models.TextField("commentaire", blank=True)
    created_at = models.DateTimeField("saisie le", default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="promotions",
        null=True,
        blank=True,
        verbose_name="saisie par",
    )
    cancelled_at = models.DateTimeField("annulée le", null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cancelled_promotions",
        null=True,
        blank=True,
        verbose_name="annulée par",
    )
    cancel_reason = models.TextField("motif de l'annulation", blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-first_week", "customer", "article"]
        verbose_name = "promotion"

    def __str__(self) -> str:
        return f"{self.customer.code} – {self.article.code} ×{self.coefficient}"

    def clean(self) -> None:
        from . import forecast

        forecast.validate_promotion(self)

    @property
    def is_cancelled(self) -> bool:
        return self.cancelled_at is not None

    @property
    def notice_days(self) -> int:
        """Délai entre l'annonce et le début de la promotion, en jours."""
        return (self.first_week - self.announced_on).days


class ImmutableQuerySet(models.QuerySet):
    def delete(self):
        raise ValidationError(self.model.immutable_message)

    def update(self, **kwargs):
        raise ValidationError(self.model.immutable_message)


class ImmutableModel(models.Model):
    """Enregistrement gardé tel quel pour l'audit : jamais modifié ni supprimé."""

    immutable_message = "Cet enregistrement ne se modifie ni ne se supprime."
    objects = ImmutableQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError(self.immutable_message)
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(self.immutable_message)


class ForecastAdjustment(ImmutableModel):
    """Correction manuelle : remplace la quantité calculée pour un produit × enseigne × semaine.

    On ne la modifie jamais : une nouvelle correction remplace la précédente. Une correction
    sans quantité rend la main au calcul.
    """

    immutable_message = (
        "Une correction ne se modifie ni ne se supprime : saisis une nouvelle correction."
    )

    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="forecast_adjustments",
        verbose_name="enseigne",
    )  # fmt: skip
    article = models.ForeignKey(
        Article, on_delete=models.PROTECT, related_name="forecast_adjustments",
        verbose_name="produit fini",
    )  # fmt: skip
    week = models.DateField("semaine (lundi)")
    quantity = models.DecimalField(
        "quantité prévue",
        **QUANTITY,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Vide = retour à la quantité calculée.",
    )
    reason = models.TextField("motif")
    created_at = models.DateTimeField("saisie le", default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="forecast_adjustments",
        null=True,
        blank=True,
        verbose_name="saisie par",
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "correction de prévision"
        verbose_name_plural = "corrections de prévision"

    def __str__(self) -> str:
        return f"{self.customer.code} – {self.article.code} – {self.week}"

    def clean(self) -> None:
        if not (self.reason or "").strip():
            raise ValidationError({"reason": "Indique le motif de la correction."})
        if self.week and self.week.weekday() != 0:
            raise ValidationError({"week": "Une semaine est désignée par son lundi."})


class VersionSource(models.TextChoices):
    AUTOMATIC = "auto", "Automatique (lundi)"
    MANUAL = "manuel", "À la demande"


class ForecastVersion(ImmutableModel):
    """Photo de la prévision à 8 semaines à un instant donné. Jamais modifiée."""

    immutable_message = "Une version de prévision figée ne se modifie ni ne se supprime."

    number = models.CharField("numéro", max_length=20, unique=True)
    created_at = models.DateTimeField("figée le", default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="forecast_versions",
        null=True,
        blank=True,
        verbose_name="figée par",
    )
    source = models.CharField("origine", max_length=10, choices=VersionSource.choices)
    first_week = models.DateField("première semaine prévue (lundi)")
    comment = models.TextField("commentaire", blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "version de prévision"
        verbose_name_plural = "versions de prévision"

    def __str__(self) -> str:
        return self.number


class ForecastLine(ImmutableModel):
    """Quantité prévue d'un produit pour une enseigne et une semaine, avec son détail."""

    immutable_message = "Une ligne de prévision figée ne se modifie ni ne se supprime."

    version = models.ForeignKey(
        ForecastVersion, on_delete=models.PROTECT, related_name="lines", verbose_name="version"
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="forecast_lines", verbose_name="enseigne"
    )
    article = models.ForeignKey(
        Article, on_delete=models.PROTECT, related_name="forecast_lines", verbose_name="produit"
    )
    week = models.DateField("semaine (lundi)")
    base_quantity = models.DecimalField("quantité calculée", **QUANTITY)
    promotion = models.ForeignKey(
        Promotion, on_delete=models.PROTECT, null=True, blank=True, verbose_name="promotion"
    )
    promo_coefficient = models.DecimalField(
        "coefficient promotion", max_digits=4, decimal_places=2, null=True, blank=True
    )
    adjustment = models.ForeignKey(
        ForecastAdjustment, on_delete=models.PROTECT, null=True, blank=True,
        verbose_name="correction",
    )  # fmt: skip
    quantity = models.DecimalField("quantité prévue", **QUANTITY)

    class Meta:
        ordering = ["version", "week", "customer", "article"]
        verbose_name = "ligne de prévision"
        verbose_name_plural = "lignes de prévision"
        constraints = [
            models.UniqueConstraint(
                fields=["version", "customer", "article", "week"],
                name="unique_forecast_line_per_version",
            )
        ]

    def __str__(self) -> str:
        return f"{self.version.number} – {self.article.code} – {self.week} : {self.quantity}"
