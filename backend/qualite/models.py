"""Rappels produit (règle 9)."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from stocks.models import Lot


class ProductRecall(models.Model):
    """Rappel officiel lancé par la qualité à partir d'un lot. Jamais modifié.

    `snapshot` garde la photo complète au moment du lancement (lots concernés, stocks,
    livraisons) : c'est la preuve pour les autorités et les audits IFS / BRCGS.
    """

    number = models.CharField("numéro", max_length=20, unique=True)
    origin_lot = models.ForeignKey(
        Lot, on_delete=models.PROTECT, related_name="recalls", verbose_name="lot d'origine"
    )
    reason = models.TextField("motif")
    created_at = models.DateTimeField("lancé le", auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="product_recalls",
        null=True,
        blank=True,
        verbose_name="lancé par",
    )
    blocked_lots = models.ManyToManyField(
        Lot, related_name="blocking_recalls", blank=True, verbose_name="lots bloqués"
    )
    snapshot = models.JSONField("photo du rappel", default=dict)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "rappel produit"
        verbose_name_plural = "rappels produit"

    def __str__(self) -> str:
        return f"{self.number} – lot {self.origin_lot.number}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("Un rappel lancé ne se modifie pas.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Un rappel ne se supprime pas.")
