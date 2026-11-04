"""Lots et mouvements de stock (règles 2, 6 et 11)."""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from simple_history.models import HistoricalRecords

from referentiel.choices import DateType
from referentiel.models import Article, Location, Supplier, ValidatedModel

from .choices import LotStatus, MovementType


class Lot(ValidatedModel):
    """Règle 2 : tout stock est géré par lot."""

    number = models.CharField("numéro de lot", max_length=30, unique=True)
    article = models.ForeignKey(
        Article, on_delete=models.PROTECT, related_name="lots", verbose_name="article"
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="lots",
        null=True,
        blank=True,
        verbose_name="fournisseur",
    )
    supplier_lot_number = models.CharField("lot fournisseur", max_length=50, blank=True)
    reception_date = models.DateField("date de réception", null=True, blank=True)
    # Règle 3 : DLC pour le frais, DDM pour le sec (copié de l'article à la création)
    date_type = models.CharField("type de date", max_length=10, choices=DateType.choices)
    expiry_date = models.DateField("DLC / DDM", null=True, blank=True)
    initial_quantity = models.DecimalField("quantité initiale", max_digits=14, decimal_places=3)
    location = models.ForeignKey(
        Location, on_delete=models.PROTECT, related_name="lots", verbose_name="emplacement"
    )
    status = models.CharField("statut", max_length=20, choices=LotStatus.choices)
    block_reason = models.TextField("motif de blocage", blank=True)
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at", "number"]
        verbose_name = "lot"

    def __str__(self) -> str:
        return f"{self.number} – {self.article.code}"

    def clean(self) -> None:
        errors = {}
        if self.date_type != DateType.NONE and not self.expiry_date:
            errors["expiry_date"] = f"La {self.date_type} est obligatoire pour ce lot."
        if self.status == LotStatus.BLOCKED and not self.block_reason:
            errors["block_reason"] = "Indique le motif du blocage."
        if errors:
            raise ValidationError(errors)

    @property
    def unit(self) -> str:
        return self.article.unit

    @property
    def quantity(self) -> Decimal:
        """Quantité en stock = somme des mouvements (règle 11)."""
        total = self.movements.aggregate(total=Sum("quantity"))["total"]
        return total or Decimal("0")


class StockMovementQuerySet(models.QuerySet):
    def delete(self):
        raise ValidationError(
            "Un mouvement de stock ne se supprime jamais : passe un mouvement inverse."
        )

    def update(self, **kwargs):
        raise ValidationError(
            "Un mouvement de stock ne se modifie jamais : passe un mouvement inverse."
        )


class StockMovement(models.Model):
    """Règle 11 : aucun stock ne change sans mouvement (qui, quand, quoi, pourquoi).

    Un mouvement enregistré ne peut être ni modifié ni supprimé.
    """

    lot = models.ForeignKey(
        Lot, on_delete=models.PROTECT, related_name="movements", verbose_name="lot"
    )
    movement_type = models.CharField("type", max_length=20, choices=MovementType.choices)
    quantity = models.DecimalField(
        "quantité",
        max_digits=14,
        decimal_places=3,
        help_text="Positive en entrée, négative en sortie.",
    )
    location = models.ForeignKey(
        Location, on_delete=models.PROTECT, related_name="movements", verbose_name="emplacement"
    )
    created_at = models.DateTimeField("date", auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stock_movements",
        null=True,
        blank=True,
        verbose_name="utilisateur",
    )
    reason = models.CharField("motif", max_length=200)
    reference = models.CharField("document d'origine", max_length=30, blank=True)

    objects = StockMovementQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "mouvement de stock"
        verbose_name_plural = "mouvements de stock"

    def __str__(self) -> str:
        label = self.get_movement_type_display()
        return f"{label} {self.quantity} {self.lot.unit} – {self.lot.number}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError(
                "Un mouvement de stock ne se modifie jamais : passe un mouvement inverse."
            )
        if self.quantity == 0:
            raise ValidationError({"quantity": "Un mouvement ne peut pas être de quantité nulle."})
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "Un mouvement de stock ne se supprime jamais : passe un mouvement inverse."
        )
