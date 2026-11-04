"""Lots et mouvements de stock (règles 2, 6 et 11)."""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone
from simple_history.models import HistoricalRecords

from referentiel.choices import DateType
from referentiel.models import (
    Article,
    CustomerWarehouse,
    Location,
    Site,
    Supplier,
    ValidatedModel,
)

from .choices import AlertLevel, AlertType, InventoryStatus, LotStatus, MovementType


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
    # Règle 2 : date de fabrication pour un semi-fini ou un produit fini
    production_date = models.DateField("date de fabrication", null=True, blank=True)
    # Règle 3 : DLC pour le frais, DDM pour le sec (copié de l'article à la création)
    date_type = models.CharField("type de date", max_length=10, choices=DateType.choices)
    expiry_date = models.DateField("DLC / DDM", null=True, blank=True)
    initial_quantity = models.DecimalField("quantité initiale", max_digits=14, decimal_places=3)
    # Emplacement où le lot est entré en stock ; le stock actuel par emplacement
    # se calcule à partir des mouvements (un lot peut être réparti sur plusieurs)
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="lots",
        verbose_name="emplacement d'entrée",
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
    corrected_movement = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="corrections",
        null=True,
        blank=True,
        verbose_name="mouvement corrigé",
    )
    # Règle 1 : une consommation est reliée au lot fabriqué (traçabilité amont / aval)
    produced_lot = models.ForeignKey(
        Lot,
        on_delete=models.PROTECT,
        related_name="consumptions",
        null=True,
        blank=True,
        verbose_name="lot fabriqué",
    )
    # Règle 1 : une expédition est reliée à l'entrepôt client livré
    customer_warehouse = models.ForeignKey(
        CustomerWarehouse,
        on_delete=models.PROTECT,
        related_name="shipments",
        null=True,
        blank=True,
        verbose_name="entrepôt client",
    )

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
        if self.movement_type == MovementType.CONSUMPTION and not self.produced_lot_id:
            raise ValidationError("Une consommation doit indiquer le lot fabriqué.")
        if self.movement_type == MovementType.SHIPMENT and not self.customer_warehouse_id:
            raise ValidationError("Une expédition doit indiquer l'entrepôt client livré.")
        # Inventaire : un emplacement en cours de comptage est gelé
        if self.movement_type != MovementType.INVENTORY:
            inventory = Inventory.open_on(self.location)
            if inventory is not None:
                raise ValidationError(
                    f"L'emplacement {self.location.code} est en cours d'inventaire "
                    f"({inventory.number}) : aucun mouvement avant sa validation ou son annulation."
                )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "Un mouvement de stock ne se supprime jamais : passe un mouvement inverse."
        )


class LotStatusChange(models.Model):
    """Journal des changements de statut d'un lot (qui, quand, pourquoi). Jamais modifié."""

    lot = models.ForeignKey(
        Lot, on_delete=models.PROTECT, related_name="status_changes", verbose_name="lot"
    )
    from_status = models.CharField("ancien statut", max_length=20, choices=LotStatus.choices)
    to_status = models.CharField("nouveau statut", max_length=20, choices=LotStatus.choices)
    reason = models.TextField("motif", blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="lot_status_changes",
        null=True,
        blank=True,
        verbose_name="utilisateur",
        help_text="Vide = changement automatique par l'ERP.",
    )
    changed_at = models.DateTimeField("date", auto_now_add=True)

    class Meta:
        ordering = ["-changed_at", "-id"]
        verbose_name = "changement de statut"
        verbose_name_plural = "changements de statut"

    def __str__(self) -> str:
        return f"{self.lot.number} : {self.from_status} → {self.to_status}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("Un changement de statut enregistré ne se modifie pas.")
        super().save(*args, **kwargs)


# --- Relevés de température (règle 7) ----------------------------------------


class TemperatureReading(models.Model):
    """Relevé de température d'un emplacement. Jamais modifié ni supprimé."""

    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="temperature_readings",
        verbose_name="emplacement",
    )
    temperature = models.DecimalField("température (°C)", max_digits=4, decimal_places=1)
    measured_at = models.DateTimeField("relevé le", default=timezone.now)
    # Limites en vigueur au moment du relevé (gardées pour l'audit)
    min_allowed = models.DecimalField(
        "mini autorisé (°C)", max_digits=4, decimal_places=1, null=True, blank=True
    )
    max_allowed = models.DecimalField(
        "maxi autorisé (°C)", max_digits=4, decimal_places=1, null=True, blank=True
    )
    is_compliant = models.BooleanField("conforme", default=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="temperature_readings",
        null=True,
        blank=True,
        verbose_name="relevé par",
    )
    comment = models.TextField("commentaire", blank=True)

    class Meta:
        ordering = ["-measured_at", "-id"]
        verbose_name = "relevé de température"
        verbose_name_plural = "relevés de température"

    def __str__(self) -> str:
        return f"{self.location.code} : {self.temperature} °C"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("Un relevé de température enregistré ne se modifie pas.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Un relevé de température ne se supprime pas.")


# --- Inventaires -------------------------------------------------------------


class Inventory(models.Model):
    number = models.CharField("numéro", max_length=20, unique=True)
    site = models.ForeignKey(
        Site, on_delete=models.PROTECT, related_name="inventories", verbose_name="site"
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="inventories",
        null=True,
        blank=True,
        verbose_name="emplacement",
        help_text="Vide = tout le site.",
    )
    status = models.CharField(
        "statut", max_length=20, choices=InventoryStatus.choices, default=InventoryStatus.OPEN
    )
    comment = models.TextField("commentaire", blank=True)
    opened_at = models.DateTimeField("ouvert le", auto_now_add=True)
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="opened_inventories",
        null=True,
        blank=True,
        verbose_name="ouvert par",
    )
    closed_at = models.DateTimeField("clos le", null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="closed_inventories",
        null=True,
        blank=True,
        verbose_name="clos par",
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["-opened_at", "-id"]
        verbose_name = "inventaire"

    def __str__(self) -> str:
        scope = self.location.code if self.location_id else f"site {self.site.code}"
        return f"{self.number} – {scope}"

    @classmethod
    def open_on(cls, location: Location) -> Inventory | None:
        """Inventaire en cours qui gèle cet emplacement (sur l'emplacement ou tout son site)."""
        return (
            cls.objects.filter(status=InventoryStatus.OPEN)
            .filter(Q(location=location) | Q(location__isnull=True, site_id=location.site_id))
            .first()
        )

    def covers(self, location: Location) -> bool:
        if self.location_id:
            return location.pk == self.location_id
        return location.site_id == self.site_id


class InventoryLine(models.Model):
    inventory = models.ForeignKey(
        Inventory, on_delete=models.CASCADE, related_name="lines", verbose_name="inventaire"
    )
    lot = models.ForeignKey(
        Lot, on_delete=models.PROTECT, related_name="inventory_lines", verbose_name="lot"
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="inventory_lines",
        verbose_name="emplacement",
    )
    expected_quantity = models.DecimalField("quantité théorique", max_digits=14, decimal_places=3)
    counted_quantity = models.DecimalField(
        "quantité comptée", max_digits=14, decimal_places=3, null=True, blank=True
    )
    added_during_count = models.BooleanField("lot trouvé pendant le comptage", default=False)
    comment = models.CharField("commentaire", max_length=200, blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["location__code", "lot__article__code", "lot__number"]
        verbose_name = "ligne d'inventaire"
        verbose_name_plural = "lignes d'inventaire"
        constraints = [
            models.UniqueConstraint(
                fields=["inventory", "lot", "location"],
                name="unique_lot_location_per_inventory",
                violation_error_message="Ce lot figure déjà à cet emplacement dans l'inventaire.",
            )
        ]

    def __str__(self) -> str:
        return f"{self.inventory.number} : {self.lot.number} en {self.location.code}"

    @property
    def difference(self) -> Decimal | None:
        if self.counted_quantity is None:
            return None
        return self.counted_quantity - self.expected_quantity


# --- Alertes -----------------------------------------------------------------


class Alert(models.Model):
    """Alerte à traiter (péremption, température…). Jamais supprimée : on la marque traitée."""

    alert_type = models.CharField("type", max_length=30, choices=AlertType.choices)
    level = models.CharField("niveau", max_length=20, choices=AlertLevel.choices)
    message = models.TextField("message")
    lot = models.ForeignKey(
        Lot,
        on_delete=models.PROTECT,
        related_name="alerts",
        null=True,
        blank=True,
        verbose_name="lot",
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="alerts",
        null=True,
        blank=True,
        verbose_name="emplacement",
    )
    temperature_reading = models.ForeignKey(
        TemperatureReading,
        on_delete=models.PROTECT,
        related_name="alerts",
        null=True,
        blank=True,
        verbose_name="relevé",
    )
    created_at = models.DateTimeField("créée le", auto_now_add=True)
    resolved_at = models.DateTimeField("traitée le", null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="resolved_alerts",
        null=True,
        blank=True,
        verbose_name="traitée par",
    )
    resolution_comment = models.TextField("commentaire de traitement", blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "alerte"

    def __str__(self) -> str:
        return f"{self.get_alert_type_display()} – {self.message[:60]}"

    @property
    def is_open(self) -> bool:
        return self.resolved_at is None

    def delete(self, *args, **kwargs):
        raise ValidationError("Une alerte ne se supprime pas : marque-la comme traitée.")
