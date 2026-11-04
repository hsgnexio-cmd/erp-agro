"""Données de référence de l'ERP : sites, articles, nomenclatures, fournisseurs, clients."""

from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from simple_history.models import HistoricalRecords

from . import services
from .choices import (
    ArticleType,
    CustomerType,
    DateType,
    SiteType,
    TemperatureClass,
    Unit,
)

THREE_LETTERS = RegexValidator(r"^[A-Z]{3}$", "Le code doit comporter 3 lettres majuscules.")


class ValidatedModel(models.Model):
    """Vérifie toutes les règles avant chaque enregistrement, quel que soit le chemin."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# --- Sites ------------------------------------------------------------------


class Site(ValidatedModel):
    code = models.CharField("code", max_length=3, unique=True, validators=[THREE_LETTERS])
    name = models.CharField("nom", max_length=100)
    site_type = models.CharField("type", max_length=20, choices=SiteType.choices)
    city = models.CharField("ville", max_length=100, blank=True)
    active = models.BooleanField("actif", default=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["code"]
        verbose_name = "site"

    def __str__(self) -> str:
        return f"{self.code} – {self.name}"


class Location(ValidatedModel):
    site = models.ForeignKey(
        Site, on_delete=models.PROTECT, related_name="locations", verbose_name="site"
    )
    code = models.CharField("code", max_length=20, unique=True)
    name = models.CharField("nom", max_length=100)
    temperature_class = models.CharField(
        "classe de température", max_length=20, choices=TemperatureClass.choices
    )
    min_temperature = models.DecimalField(
        "température mini (°C)", max_digits=4, decimal_places=1, null=True, blank=True
    )
    max_temperature = models.DecimalField(
        "température maxi (°C)", max_digits=4, decimal_places=1, null=True, blank=True
    )
    active = models.BooleanField("actif", default=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["code"]
        verbose_name = "emplacement"

    def __str__(self) -> str:
        return f"{self.code} – {self.name}"

    def clean(self) -> None:
        self.code = self.code.strip().upper()
        services.validate_location(self)


# --- Classifications ---------------------------------------------------------


class ProductFamily(ValidatedModel):
    code = models.CharField("code", max_length=3, unique=True, validators=[THREE_LETTERS])
    name = models.CharField("nom", max_length=100)
    site = models.ForeignKey(
        Site, on_delete=models.PROTECT, related_name="families", verbose_name="usine"
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["code"]
        verbose_name = "famille de produits"
        verbose_name_plural = "familles de produits"

    def __str__(self) -> str:
        return f"{self.code} – {self.name}"

    def clean(self) -> None:
        services.validate_product_family(self)


class MaterialCategory(ValidatedModel):
    code = models.CharField("code", max_length=3, unique=True, validators=[THREE_LETTERS])
    name = models.CharField("nom", max_length=100)
    temperature_class = models.CharField(
        "conservation", max_length=20, choices=TemperatureClass.choices
    )
    # Règle 3 : DDM pour les produits secs, DLC pour les produits frais
    date_type = models.CharField(
        "type de date",
        max_length=10,
        choices=[(DateType.DLC, DateType.DLC.label), (DateType.DDM, DateType.DDM.label)],
    )
    # Contrôle à réception : part minimale de la durée de vie qui doit rester
    min_remaining_shelf_life_pct = models.DecimalField(
        "DLC restante minimale à réception (%)",
        max_digits=5,
        decimal_places=2,
        default=Decimal("50"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["code"]
        verbose_name = "catégorie de matières"
        verbose_name_plural = "catégories de matières"

    def __str__(self) -> str:
        return f"{self.code} – {self.name}"


class Allergen(models.Model):
    """Les 14 allergènes réglementaires (règlement UE n° 1169/2011), créés par migration."""

    code = models.SlugField("code", max_length=30, unique=True)
    name = models.CharField("nom", max_length=100)
    order = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = "allergène"

    def __str__(self) -> str:
        return self.name


# --- Clients (enseignes) ----------------------------------------------------


class Customer(ValidatedModel):
    code = models.CharField(
        "code",
        max_length=10,
        unique=True,
        validators=[RegexValidator(r"^ENS\d+$", "Le code enseigne suit le format ENS1, ENS2…")],
    )
    name = models.CharField("nom", max_length=100)
    customer_type = models.CharField("type", max_length=20, choices=CustomerType.choices)
    sells_brand = models.BooleanField("vend la marque Brévanne", default=True)
    sells_private_label = models.BooleanField("vend du MDD", default=False)
    # Règle 5 : durée de vie restante minimale exigée à la livraison
    min_remaining_shelf_life_pct = models.DecimalField(
        "DLC minimale à la livraison (%)",
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        help_text="Part minimale de la durée de vie totale qui doit rester à la livraison.",
    )
    active = models.BooleanField("actif", default=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["code"]
        verbose_name = "enseigne"

    def __str__(self) -> str:
        return f"{self.code} – {self.name}"

    def clean(self) -> None:
        services.validate_customer(self)


class CustomerWarehouse(ValidatedModel):
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="warehouses", verbose_name="enseigne"
    )
    code = models.CharField("code", max_length=20, unique=True)
    name = models.CharField("nom", max_length=100)
    address = models.CharField("adresse", max_length=200, blank=True)
    postal_code = models.CharField("code postal", max_length=10, blank=True)
    city = models.CharField("ville", max_length=100)
    active = models.BooleanField("actif", default=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["code"]
        verbose_name = "entrepôt client"
        verbose_name_plural = "entrepôts clients"

    def __str__(self) -> str:
        return f"{self.code} – {self.name}"

    def clean(self) -> None:
        self.code = self.code.strip().upper()
        services.validate_customer_warehouse(self)


# --- Recettes et articles ---------------------------------------------------


class Recipe(ValidatedModel):
    """Recette commune à toutes ses versions (marque Brévanne et MDD) — règle 10."""

    code = models.CharField(
        "code",
        max_length=10,
        unique=True,
        validators=[
            RegexValidator(r"^[A-Z0-9]{2,10}$", "Le code recette : lettres majuscules et chiffres.")
        ],
    )
    name = models.CharField("nom", max_length=150)
    family = models.ForeignKey(
        ProductFamily, on_delete=models.PROTECT, related_name="recipes", verbose_name="famille"
    )
    active = models.BooleanField("active", default=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["code"]
        verbose_name = "recette"

    def __str__(self) -> str:
        return f"{self.code} – {self.name}"


class Article(ValidatedModel):
    """Matière première, semi-fini, produit fini ou emballage."""

    code = models.CharField(
        "code",
        max_length=40,
        unique=True,
        blank=True,
        help_text="Généré automatiquement pour les produits finis.",
    )
    name = models.CharField("désignation", max_length=200)
    article_type = models.CharField("type", max_length=2, choices=ArticleType.choices)
    unit = models.CharField("unité de stock", max_length=2, choices=Unit.choices)
    category = models.ForeignKey(
        MaterialCategory,
        on_delete=models.PROTECT,
        related_name="articles",
        null=True,
        blank=True,
        verbose_name="catégorie (matières)",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.PROTECT,
        related_name="articles",
        null=True,
        blank=True,
        verbose_name="recette (produits finis)",
    )
    brand_customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="private_label_articles",
        null=True,
        blank=True,
        verbose_name="enseigne MDD",
        help_text="Vide = marque Brévanne.",
    )
    format_size = models.PositiveIntegerField("format (g)", null=True, blank=True)
    shelf_life_days = models.PositiveSmallIntegerField(
        "durée de vie (jours)", null=True, blank=True
    )
    # Déduits automatiquement (voir services.prepare_and_validate_article)
    date_type = models.CharField(
        "type de date", max_length=10, choices=DateType.choices, editable=False, blank=True
    )
    storage_temperature_class = models.CharField(
        "conservation",
        max_length=20,
        choices=TemperatureClass.choices,
        editable=False,
        blank=True,
    )
    technical_sheet = models.TextField("fiche technique", blank=True)
    specifications = models.TextField("cahier des charges", blank=True)
    allergens = models.ManyToManyField(
        Allergen, related_name="articles", blank=True, verbose_name="allergènes"
    )
    active = models.BooleanField("actif", default=True)
    history = HistoricalRecords(m2m_fields=[allergens])

    class Meta:
        ordering = ["code"]
        verbose_name = "article"

    def __str__(self) -> str:
        return f"{self.code} – {self.name}"

    def clean(self) -> None:
        services.prepare_and_validate_article(self)

    @property
    def brand_code(self) -> str:
        if self.article_type != ArticleType.FINISHED_PRODUCT:
            return ""
        return self.brand_customer.code if self.brand_customer_id else services.OWN_BRAND_CODE


# --- Nomenclatures ----------------------------------------------------------


class BillOfMaterials(ValidatedModel):
    """Nomenclature d'un semi-fini ou d'un produit fini."""

    article = models.OneToOneField(
        Article, on_delete=models.PROTECT, related_name="bom", verbose_name="article fabriqué"
    )
    base_quantity = models.DecimalField(
        "quantité de base",
        max_digits=12,
        decimal_places=3,
        default=Decimal("1"),
        validators=[MinValueValidator(Decimal("0.001"))],
        help_text="Quantité fabriquée (dans l'unité de l'article) pour les quantités indiquées.",
    )
    comment = models.TextField("commentaire", blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["article__code"]
        verbose_name = "nomenclature"

    def __str__(self) -> str:
        return f"Nomenclature {self.article.code}"

    def clean(self) -> None:
        services.validate_bom(self)


class BOMLine(ValidatedModel):
    bom = models.ForeignKey(
        BillOfMaterials, on_delete=models.CASCADE, related_name="lines", verbose_name="nomenclature"
    )
    component = models.ForeignKey(
        Article, on_delete=models.PROTECT, related_name="used_in", verbose_name="composant"
    )
    quantity = models.DecimalField(
        "quantité nette",
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0001"))],
    )
    unit = models.CharField("unité", max_length=2, choices=Unit.choices)
    loss_rate = models.DecimalField(
        "taux de perte (%)",
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("99.99"))],
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["bom", "id"]
        verbose_name = "ligne de nomenclature"
        verbose_name_plural = "lignes de nomenclature"
        constraints = [
            models.UniqueConstraint(
                fields=["bom", "component"],
                name="unique_component_per_bom",
                violation_error_message="Ce composant figure déjà dans la nomenclature.",
            )
        ]

    def __str__(self) -> str:
        return f"{self.component.code} : {self.quantity} {self.unit}"

    def clean(self) -> None:
        services.validate_bom_line(self)

    @property
    def gross_quantity(self) -> Decimal:
        return services.gross_quantity(self)


# --- Fournisseurs -----------------------------------------------------------


class Supplier(ValidatedModel):
    code = models.CharField(
        "code",
        max_length=10,
        unique=True,
        validators=[RegexValidator(r"^FOU-\d{3}$", "Le code fournisseur suit le format FOU-001.")],
    )
    name = models.CharField("raison sociale", max_length=150)
    address = models.CharField("adresse", max_length=200, blank=True)
    postal_code = models.CharField("code postal", max_length=10, blank=True)
    city = models.CharField("ville", max_length=100, blank=True)
    country = models.CharField("pays", max_length=100, default="France")
    email = models.EmailField("e-mail", blank=True)
    phone = models.CharField("téléphone", max_length=30, blank=True)
    lead_time_days = models.PositiveSmallIntegerField("délai de livraison (jours)")
    categories = models.ManyToManyField(
        MaterialCategory, related_name="suppliers", blank=True, verbose_name="catégories fournies"
    )
    audited = models.BooleanField("audité", default=False)
    last_audit_date = models.DateField("date du dernier audit", null=True, blank=True)
    active = models.BooleanField("actif", default=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["code"]
        verbose_name = "fournisseur"

    def __str__(self) -> str:
        return f"{self.code} – {self.name}"

    def clean(self) -> None:
        services.validate_supplier(self)


class SupplierArticle(ValidatedModel):
    """Article référencé chez un fournisseur."""

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="supplied_articles",
        verbose_name="fournisseur",
    )
    article = models.ForeignKey(
        Article, on_delete=models.PROTECT, related_name="supplier_links", verbose_name="article"
    )
    supplier_reference = models.CharField("référence fournisseur", max_length=50, blank=True)
    is_main_supplier = models.BooleanField("fournisseur principal", default=False)
    min_order_quantity = models.DecimalField(
        "quantité minimale de commande",
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.001"))],
        help_text="Dans l'unité de stock de l'article. Vide = pas de minimum.",
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["supplier", "article"]
        verbose_name = "article fournisseur"
        verbose_name_plural = "articles fournisseurs"
        constraints = [
            models.UniqueConstraint(
                fields=["supplier", "article"],
                name="unique_article_per_supplier",
                violation_error_message="Cet article est déjà référencé chez ce fournisseur.",
            )
        ]

    def __str__(self) -> str:
        return f"{self.supplier.code} → {self.article.code}"

    def clean(self) -> None:
        services.validate_supplier_article(self)


# --- Numérotation automatique -------------------------------------------------


class DocumentSequence(models.Model):
    """Dernier numéro attribué pour un préfixe (ex. « CA-2026 » → CA-2026-00042)."""

    key = models.CharField("préfixe", max_length=30, unique=True)
    last_value = models.PositiveIntegerField("dernier numéro", default=0)

    class Meta:
        verbose_name = "compteur de numérotation"
        verbose_name_plural = "compteurs de numérotation"

    def __str__(self) -> str:
        return f"{self.key} : {self.last_value}"
