"""Tarifs de vente, commandes clients et messages EDI."""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from simple_history.models import HistoricalRecords

from referentiel.models import Article, Customer, CustomerWarehouse, ValidatedModel


class SalePrice(ValidatedModel):
    """Prix de vente HT d'un produit fini pour une enseigne, sur une période."""

    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="sale_prices", verbose_name="enseigne"
    )
    article = models.ForeignKey(
        Article, on_delete=models.PROTECT, related_name="sale_prices", verbose_name="produit fini"
    )
    unit_price = models.DecimalField(
        "prix unitaire HT (€)",
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0001"))],
    )
    valid_from = models.DateField("valable du")
    valid_to = models.DateField("valable jusqu'au", null=True, blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["customer", "article", "-valid_from"]
        verbose_name = "tarif de vente"
        verbose_name_plural = "tarifs de vente"

    def __str__(self) -> str:
        return f"{self.customer.code} – {self.article.code} : {self.unit_price} €"

    def clean(self) -> None:
        from . import orders

        orders.validate_sale_price(self)


class OrderStatus(models.TextChoices):
    RECEIVED = "recue", "Reçue"
    PREPARING = "en_preparation", "En préparation"
    SHIPPED = "expediee", "Expédiée"
    CANCELLED = "annulee", "Annulée"


class OrderSource(models.TextChoices):
    EDI = "edi", "EDI"
    MANUAL = "manuel", "Saisie manuelle"


class EdiStatus(models.TextChoices):
    RECEIVED = "recu", "Reçu"
    INTEGRATED = "integre", "Intégré"
    REJECTED = "rejete", "Rejeté"


class EdiMessage(models.Model):
    """Message de commande reçu d'une enseigne (EDI simulé). Gardé tel quel pour l'audit."""

    message_id = models.CharField("identifiant du message", max_length=50)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="edi_messages",
        null=True,
        blank=True,
        verbose_name="enseigne émettrice",
    )
    received_at = models.DateTimeField("reçu le")
    payload = models.JSONField("contenu du message")
    status = models.CharField(
        "statut", max_length=10, choices=EdiStatus.choices, default=EdiStatus.RECEIVED
    )
    errors = models.JSONField("motifs de rejet", default=list, blank=True)

    class Meta:
        ordering = ["-received_at", "-id"]
        verbose_name = "message EDI"
        verbose_name_plural = "messages EDI"

    def __str__(self) -> str:
        return f"{self.message_id} ({self.get_status_display()})"


class CustomerOrder(models.Model):
    number = models.CharField("numéro", max_length=20, unique=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="orders", verbose_name="enseigne"
    )
    warehouse = models.ForeignKey(
        CustomerWarehouse,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="entrepôt livré",
    )
    customer_reference = models.CharField("référence de l'enseigne", max_length=50, blank=True)
    received_at = models.DateTimeField("reçue le")
    requested_delivery_date = models.DateField("livraison demandée")
    # Phase 11 : dernier jour d'expédition de la plateforme avant la livraison (transport J+1),
    # calculé avec le calendrier à la prise de commande ; sert au taux de service
    ship_by_date = models.DateField("à expédier au plus tard le", null=True, blank=True)
    status = models.CharField(
        "statut", max_length=20, choices=OrderStatus.choices, default=OrderStatus.RECEIVED
    )
    source = models.CharField("origine", max_length=10, choices=OrderSource.choices)
    edi_message = models.OneToOneField(
        EdiMessage,
        on_delete=models.PROTECT,
        related_name="order",
        null=True,
        blank=True,
        verbose_name="message EDI",
    )
    comment = models.TextField("commentaire", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="customer_orders",
        null=True,
        blank=True,
        verbose_name="saisie par",
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["-received_at", "-id"]
        verbose_name = "commande client"
        verbose_name_plural = "commandes clients"

    def __str__(self) -> str:
        return f"{self.number} – {self.customer.code}"

    @property
    def total_amount(self) -> Decimal:
        return sum((line.amount or Decimal("0") for line in self.lines.all()), Decimal("0"))


class CustomerOrderLine(models.Model):
    order = models.ForeignKey(
        CustomerOrder, on_delete=models.CASCADE, related_name="lines", verbose_name="commande"
    )
    article = models.ForeignKey(
        Article,
        on_delete=models.PROTECT,
        related_name="customer_order_lines",
        verbose_name="produit",
    )
    quantity = models.DecimalField(
        "quantité commandée",
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("1"))],
    )
    unit_price = models.DecimalField(
        "prix unitaire HT (€)",
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Vide = aucun tarif en vigueur : ligne à valoriser.",
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "ligne de commande client"
        verbose_name_plural = "lignes de commande client"
        constraints = [
            models.UniqueConstraint(
                fields=["order", "article"],
                name="unique_article_per_customer_order",
                violation_error_message="Ce produit figure déjà dans la commande.",
            )
        ]

    def __str__(self) -> str:
        return f"{self.article.code} × {self.quantity}"

    @property
    def amount(self) -> Decimal | None:
        if self.unit_price is None:
            return None
        return (self.quantity * self.unit_price).quantize(Decimal("0.01"))


# --- Préparation et expédition (partie 7b) ---------------------------------------------


class ShipmentStatus(models.TextChoices):
    PREPARED = "preparee", "Préparée"
    SHIPPED = "expediee", "Expédiée"
    REFUSED = "refusee", "Refusée (température)"
    CANCELLED = "annulee", "Préparation annulée"


# Une commande n'a qu'un seul bon de livraison en cours ou expédié (pas de reliquat)
OPEN_SHIPMENT_STATUSES = [ShipmentStatus.PREPARED, ShipmentStatus.SHIPPED]


class Shipment(models.Model):
    """Bon de livraison : préparation (lots choisis), puis expédition (mouvements de stock)."""

    number = models.CharField("numéro", max_length=20, unique=True)
    order = models.ForeignKey(
        CustomerOrder, on_delete=models.PROTECT, related_name="shipments", verbose_name="commande"
    )
    status = models.CharField(
        "statut", max_length=20, choices=ShipmentStatus.choices, default=ShipmentStatus.PREPARED
    )
    prepared_at = models.DateTimeField("préparé le", auto_now_add=True)
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="prepared_shipments",
        null=True,
        blank=True,
        verbose_name="préparé par",
    )
    carrier = models.CharField("transporteur", max_length=100, blank=True)
    loading_temperature = models.DecimalField(
        "température au chargement (°C)", max_digits=4, decimal_places=1, null=True, blank=True
    )
    shipped_at = models.DateTimeField("expédié (ou contrôlé) le", null=True, blank=True)
    shipped_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="shipped_shipments",
        null=True,
        blank=True,
        verbose_name="expédié (ou contrôlé) par",
    )
    refusal_reason = models.TextField("motif du refus ou de l'annulation", blank=True)

    class Meta:
        ordering = ["-prepared_at", "-id"]
        verbose_name = "bon de livraison"
        verbose_name_plural = "bons de livraison"
        constraints = [
            models.UniqueConstraint(
                fields=["order"],
                condition=models.Q(status__in=OPEN_SHIPMENT_STATUSES),
                name="one_open_shipment_per_order",
                violation_error_message="Cette commande a déjà un bon de livraison en cours.",
            )
        ]

    def __str__(self) -> str:
        return f"{self.number} – {self.order.number}"


class ShipmentLine(models.Model):
    """Lot préparé pour une ligne de commande."""

    shipment = models.ForeignKey(
        Shipment, on_delete=models.PROTECT, related_name="lines", verbose_name="bon de livraison"
    )
    order_line = models.ForeignKey(
        CustomerOrderLine,
        on_delete=models.PROTECT,
        related_name="shipment_lines",
        verbose_name="ligne de commande",
    )
    lot = models.ForeignKey(
        "stocks.Lot", on_delete=models.PROTECT, related_name="shipment_lines", verbose_name="lot"
    )
    location = models.ForeignKey(
        "referentiel.Location",
        on_delete=models.PROTECT,
        related_name="shipment_lines",
        verbose_name="emplacement",
    )
    quantity = models.DecimalField("quantité", max_digits=12, decimal_places=3)
    fefo_justification = models.CharField("justification hors FEFO", max_length=200, blank=True)
    movement = models.OneToOneField(
        "stocks.StockMovement",
        on_delete=models.PROTECT,
        related_name="shipment_line",
        null=True,
        blank=True,
        verbose_name="mouvement d'expédition",
    )

    class Meta:
        ordering = ["shipment", "id"]
        verbose_name = "ligne préparée"
        verbose_name_plural = "lignes préparées"

    def __str__(self) -> str:
        return f"{self.lot.number} × {self.quantity}"


class Pallet(models.Model):
    """Palette expédiée, identifiée par son SSCC (norme GS1, 18 chiffres)."""

    shipment = models.ForeignKey(
        Shipment, on_delete=models.PROTECT, related_name="pallets", verbose_name="bon de livraison"
    )
    sscc = models.CharField("SSCC", max_length=18, unique=True)
    rank = models.PositiveSmallIntegerField("rang")

    class Meta:
        ordering = ["shipment", "rank"]
        verbose_name = "palette"
        verbose_name_plural = "palettes"

    def __str__(self) -> str:
        return self.sscc

    @property
    def total_quantity(self) -> Decimal:
        return sum((line.quantity for line in self.lines.all()), Decimal("0"))


class PalletLine(models.Model):
    pallet = models.ForeignKey(
        Pallet, on_delete=models.PROTECT, related_name="lines", verbose_name="palette"
    )
    shipment_line = models.ForeignKey(
        ShipmentLine,
        on_delete=models.PROTECT,
        related_name="pallet_lines",
        verbose_name="ligne préparée",
    )
    quantity = models.DecimalField("quantité", max_digits=12, decimal_places=3)

    class Meta:
        ordering = ["pallet", "id"]
        verbose_name = "contenu de palette"
        verbose_name_plural = "contenus de palettes"

    def __str__(self) -> str:
        return f"{self.pallet.sscc} : {self.shipment_line.lot.number} × {self.quantity}"
