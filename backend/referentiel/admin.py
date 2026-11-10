"""Écrans de saisie du référentiel dans l'administration Django.

Chaque écran a un bouton « Historique » qui montre qui a modifié quoi et quand.
La suppression est réservée au rôle `admin` ; une donnée déjà utilisée ailleurs
(ex. une matière présente dans une nomenclature) est protégée et ne peut pas être supprimée.
"""

from django import forms
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from . import services
from .models import (
    Allergen,
    Article,
    BillOfMaterials,
    BOMLine,
    Customer,
    CustomerWarehouse,
    Location,
    MaterialCategory,
    ProductFamily,
    ProductionLine,
    Recipe,
    Site,
    SiteClosure,
    Supplier,
    SupplierArticle,
)
from .permissions import can_edit_allergens


class LocationInline(admin.TabularInline):
    model = Location
    extra = 0


@admin.register(Site)
class SiteAdmin(SimpleHistoryAdmin):
    list_display = ("code", "name", "site_type", "city", "active")
    list_filter = ("site_type", "active")
    search_fields = ("code", "name")
    inlines = [LocationInline]


@admin.register(Location)
class LocationAdmin(SimpleHistoryAdmin):
    list_display = (
        "code",
        "name",
        "site",
        "temperature_class",
        "min_temperature",
        "max_temperature",
        "active",
    )
    list_filter = ("site", "temperature_class", "active")
    search_fields = ("code", "name")


@admin.register(ProductFamily)
class ProductFamilyAdmin(SimpleHistoryAdmin):
    list_display = ("code", "name", "site")


@admin.register(MaterialCategory)
class MaterialCategoryAdmin(SimpleHistoryAdmin):
    list_display = (
        "code",
        "name",
        "temperature_class",
        "date_type",
        "min_remaining_shelf_life_pct",
    )


@admin.register(Allergen)
class AllergenAdmin(admin.ModelAdmin):
    list_display = ("order", "name", "code")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CustomerWarehouseInline(admin.TabularInline):
    model = CustomerWarehouse
    extra = 0


@admin.register(Customer)
class CustomerAdmin(SimpleHistoryAdmin):
    list_display = (
        "code",
        "name",
        "customer_type",
        "sells_brand",
        "sells_private_label",
        "min_remaining_shelf_life_pct",
        "active",
    )
    list_filter = ("customer_type", "sells_private_label", "active")
    search_fields = ("code", "name")
    inlines = [CustomerWarehouseInline]


@admin.register(CustomerWarehouse)
class CustomerWarehouseAdmin(SimpleHistoryAdmin):
    list_display = ("code", "name", "customer", "city", "active")
    list_filter = ("customer", "active")
    search_fields = ("code", "name", "city")


@admin.register(Recipe)
class RecipeAdmin(SimpleHistoryAdmin):
    list_display = ("code", "name", "family", "active")
    list_filter = ("family", "active")
    search_fields = ("code", "name")


class ArticleAdminForm(forms.ModelForm):
    class Meta:
        model = Article
        # Les champs affichés sont définis par ArticleAdmin.fieldsets
        fields = "__all__"  # noqa: DJ007

    def clean(self):
        cleaned = super().clean()
        allergens = cleaned.get("allergens")
        if allergens:
            services.validate_allergens(
                Article(article_type=cleaned.get("article_type", "")), list(allergens)
            )
        return cleaned


@admin.register(Article)
class ArticleAdmin(SimpleHistoryAdmin):
    form = ArticleAdminForm
    list_display = (
        "code",
        "name",
        "article_type",
        "unit",
        "shelf_life_days",
        "date_type",
        "active",
    )
    list_filter = ("article_type", "category", "date_type", "brand_customer", "active")
    search_fields = ("code", "name")
    filter_horizontal = ("allergens",)
    fieldsets = (
        (None, {"fields": ("article_type", "code", "name", "unit", "active")}),
        ("Matière première", {"fields": ("category", "allergens")}),
        (
            "Produit fini",
            {"fields": ("recipe", "brand_customer", "format_size", "safety_stock_days")},
        ),
        (
            "Conservation",
            {"fields": ("shelf_life_days", "date_type", "storage_temperature_class")},
        ),
        ("Documents", {"fields": ("technical_sheet", "specifications")}),
    )

    def get_readonly_fields(self, request, obj=None):
        readonly = ["date_type", "storage_temperature_class"]
        if not can_edit_allergens(request.user):
            readonly.append("allergens")
        return readonly


class BOMLineInline(admin.TabularInline):
    model = BOMLine
    extra = 1
    autocomplete_fields = ("component",)


@admin.register(BillOfMaterials)
class BillOfMaterialsAdmin(SimpleHistoryAdmin):
    list_display = ("article", "base_quantity")
    search_fields = ("article__code", "article__name")
    autocomplete_fields = ("article",)
    inlines = [BOMLineInline]


class SupplierArticleInline(admin.TabularInline):
    model = SupplierArticle
    extra = 0
    autocomplete_fields = ("article",)


@admin.register(Supplier)
class SupplierAdmin(SimpleHistoryAdmin):
    list_display = ("code", "name", "city", "lead_time_days", "audited", "active")
    list_filter = ("categories", "audited", "active")
    search_fields = ("code", "name")
    filter_horizontal = ("categories",)
    inlines = [SupplierArticleInline]


@admin.register(ProductionLine)
class ProductionLineAdmin(SimpleHistoryAdmin):
    list_display = ("code", "name", "site", "capacity_per_hour", "formats", "active")
    list_filter = ("site", "active")
    filter_horizontal = ("families",)


@admin.register(SiteClosure)
class SiteClosureAdmin(SimpleHistoryAdmin):
    list_display = ("site", "start_date", "end_date", "reason")
    list_filter = ("site",)
