"""Tarifs fournisseurs, commandes et réceptions."""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from simple_history.models import HistoricalRecords

from referentiel.models import Article, Location, Site, Supplier, SupplierArticle, ValidatedModel
from referentiel.services import next_document_number
from stocks.models import Lot

from . import services
from .choices import PurchaseOrderStatus

POSITIVE_QUANTITY = [MinValueValidator(Decimal("0.001"))]


class SupplierPrice(ValidatedModel):
    """Prix d'achat d'un article chez un fournisseur, sur une période."""

    supplier_article = models.ForeignKey(
        SupplierArticle,
        on_delete=models.CASCADE,
        related_name="prices",
        verbose_name="article fournisseur",
    )
    unit_price = models.DecimalField(
        "prix unitaire HT (€)",
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0001"))],
        help_text="Prix par unité de stock de l'article (kg, litre ou unité).",
    )
    valid_from = models.DateField("valable du")
    valid_to = models.DateField("valable jusqu'au", null=True, blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["supplier_article", "-valid_from"]
        verbose_name = "tarif fournisseur"
        verbose_name_plural = "tarifs fournisseurs"

    def __str__(self) -> str:
        return f"{self.supplier_article} : {self.unit_price} € depuis le {self.valid_from}"

    def clean(self) -> None:
        services.validate_supplier_price(self)


class PurchaseOrder(ValidatedModel):
    number = models.CharField("numéro", max_length=20, unique=True, blank=True)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="purchase_orders",
        verbose_name="fournisseur",
    )
    delivery_site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        related_name="purchase_orders",
        verbose_name="site de livraison",
    )
    order_date = models.DateField("date de commande", default=timezone.localdate)
    expected_delivery_date = models.DateField(
        "livraison prévue",
        null=True,
        blank=True,
        help_text="Vide = date de commande + délai du fournisseur.",
    )
    status = models.CharField(
        "statut",
        max_length=25,
        choices=PurchaseOrderStatus.choices,
        default=PurchaseOrderStatus.DRAFT,
    )
    comment = models.TextField("commentaire", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchase_orders",
        null=True,
        blank=True,
        verbose_name="créée par",
    )
    created_at = models.DateTimeField("créée le", auto_now_add=True)
    sent_at = models.DateTimeField("envoyée le", null=True, blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-order_date", "-number"]
        verbose_name = "commande fournisseur"
        verbose_name_plural = "commandes fournisseurs"

    def __str__(self) -> str:
        return f"{self.number} – {self.supplier.name}"

    def clean(self) -> None:
        services.validate_purchase_order(self)

    def save(self, *args, **kwargs):
        self.full_clean()
        # Le numéro est attribué une fois la commande validée : pas de trou de numérotation
        if not self.number:
            self.number = next_document_number(f"CA-{self.order_date.year}", 5)
        models.Model.save(self, *args, **kwargs)

    @property
    def total_amount(self) -> Decimal:
        return sum((line.amount for line in self.lines.all()), Decimal("0"))


class PurchaseOrderLine(ValidatedModel):
    order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="lines", verbose_name="commande"
    )
    article = models.ForeignKey(
        Article,
        on_delete=models.PROTECT,
        related_name="purchase_order_lines",
        verbose_name="article",
    )
    quantity = models.DecimalField(
        "quantité commandée", max_digits=12, decimal_places=3, validators=POSITIVE_QUANTITY
    )
    unit = models.CharField("unité", max_length=2, editable=False, blank=True)
    unit_price = models.DecimalField(
        "prix unitaire HT (€)",
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Vide = tarif en vigueur à la date de commande.",
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "ligne de commande"
        verbose_name_plural = "lignes de commande"
        constraints = [
            models.UniqueConstraint(
                fields=["order", "article"],
                name="unique_article_per_purchase_order",
                violation_error_message="Cet article figure déjà dans la commande.",
            )
        ]

    def __str__(self) -> str:
        return f"{self.article.code} : {self.quantity} {self.unit}"

    def clean(self) -> None:
        services.prepare_and_validate_order_line(self)

    @property
    def received_quantity(self) -> Decimal:
        total = self.reception_lines.aggregate(total=Sum("quantity"))["total"]
        return total or Decimal("0")

    @property
    def amount(self) -> Decimal:
        return (self.quantity * (self.unit_price or Decimal("0"))).quantize(Decimal("0.01"))


class Reception(ValidatedModel):
    number = models.CharField("numéro", max_length=20, unique=True, blank=True)
    order = models.ForeignKey(
        PurchaseOrder, on_delete=models.PROTECT, related_name="receptions", verbose_name="commande"
    )
    received_at = models.DateTimeField("reçue le", default=timezone.now)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="receptions",
        null=True,
        blank=True,
        verbose_name="réceptionnée par",
    )
    delivery_note_number = models.CharField("n° de bon de livraison", max_length=50)
    documents_ok = models.BooleanField("documents conformes", default=True)
    location = models.ForeignKey(
        Location, on_delete=models.PROTECT, related_name="receptions", verbose_name="emplacement"
    )
    comment = models.TextField("commentaire", blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-received_at", "-number"]
        verbose_name = "réception"

    def __str__(self) -> str:
        return f"{self.number} – {self.order.number}"

    def clean(self) -> None:
        services.validate_reception(self)

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.number:
            year = timezone.localtime(self.received_at).year
            self.number = next_document_number(f"REC-{year}", 5)
        models.Model.save(self, *args, **kwargs)


class ReceptionLine(ValidatedModel):
    reception = models.ForeignKey(
        Reception, on_delete=models.CASCADE, related_name="lines", verbose_name="réception"
    )
    order_line = models.ForeignKey(
        PurchaseOrderLine,
        on_delete=models.PROTECT,
        related_name="reception_lines",
        verbose_name="ligne de commande",
    )
    quantity = models.DecimalField(
        "quantité reçue", max_digits=12, decimal_places=3, validators=POSITIVE_QUANTITY
    )
    supplier_lot_number = models.CharField("lot fournisseur", max_length=50)
    expiry_date = models.DateField("DLC / DDM", null=True, blank=True)
    temperature = models.DecimalField(
        "température mesurée (°C)", max_digits=4, decimal_places=1, null=True, blank=True
    )
    appearance_ok = models.BooleanField("aspect conforme", default=True)
    comment = models.TextField("commentaire", blank=True)
    # Résultat des contrôles, calculé automatiquement
    is_compliant = models.BooleanField("conforme", default=True, editable=False)
    non_compliance_reasons = models.TextField(
        "motifs de non-conformité", blank=True, editable=False
    )
    lot = models.OneToOneField(
        Lot,
        on_delete=models.PROTECT,
        related_name="reception_line",
        null=True,
        blank=True,
        verbose_name="lot créé",
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["reception", "id"]
        verbose_name = "ligne de réception"
        verbose_name_plural = "lignes de réception"

    def __str__(self) -> str:
        return f"{self.order_line.article.code} : {self.quantity}"
