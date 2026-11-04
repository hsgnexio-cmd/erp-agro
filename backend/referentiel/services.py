"""Règles métier du référentiel (voir CLAUDE.md, sections 4 et 5).

Ces fonctions sont appelées par les modèles avant chaque enregistrement :
une donnée qui enfreint une règle est refusée, quel que soit le chemin
(API, administration, script).
"""

import re
from decimal import Decimal

from django.core.exceptions import ValidationError

from .choices import ArticleType, DateType, SiteType, TemperatureClass, Unit

# Segment « marque » du code produit fini pour la marque propre Brévanne
OWN_BRAND_CODE = "BRE"

# Format des codes (section 5 de CLAUDE.md)
SEMI_FINISHED_CODE = re.compile(r"^SF-[A-Z0-9]+$")
PACKAGING_CODE = re.compile(r"^EM-[A-Z0-9]+-[A-Z0-9]+$")


# --- Articles ---------------------------------------------------------------


def build_finished_product_code(article) -> str:
    """Code produit fini : PF-[famille]-[recette]-[marque]-[format].

    Exemple : PF-PAT-LASBOL-BRE-300 ou PF-PAT-LASBOL-ENS2-1000.
    """
    recipe = article.recipe
    brand = article.brand_customer.code if article.brand_customer_id else OWN_BRAND_CODE
    return f"PF-{recipe.family.code}-{recipe.code}-{brand}-{article.format_size}"


def prepare_and_validate_article(article) -> None:
    """Complète les champs calculés d'un article puis vérifie les règles.

    - Le code d'un produit fini est généré automatiquement.
    - Le type de date (DLC/DDM) et la classe de température sont déduits.
    """
    errors: dict[str, list[str]] = {}

    def add(field: str, message: str) -> None:
        errors.setdefault(field, []).append(message)

    article_type = article.article_type
    article.code = (article.code or "").strip().upper()

    is_mp = article_type == ArticleType.RAW_MATERIAL
    is_pf = article_type == ArticleType.FINISHED_PRODUCT
    is_em = article_type == ArticleType.PACKAGING

    # Champs réservés à certains types d'articles
    if is_mp and not article.category_id:
        add("category", "Une matière première doit avoir une catégorie.")
    if not is_mp and article.category_id:
        add("category", "Seules les matières premières ont une catégorie.")

    if is_pf:
        if not article.recipe_id:
            add("recipe", "Un produit fini doit être rattaché à une recette.")
        if not article.format_size:
            add("format_size", "Un produit fini doit avoir un format (en grammes).")
        if article.unit != Unit.UNIT:
            add("unit", "Un produit fini se gère à l'unité (barquette, pot).")
        # Règle 10 : une version MDD n'existe que pour une enseigne qui vend du MDD
        if article.brand_customer_id and not article.brand_customer.sells_private_label:
            add(
                "brand_customer",
                f"L'enseigne {article.brand_customer.code} ne vend pas de produits "
                "en marque distributeur (MDD).",
            )
    else:
        if article.recipe_id:
            add("recipe", "Seuls les produits finis sont rattachés à une recette.")
        if article.brand_customer_id:
            add("brand_customer", "Seuls les produits finis peuvent être en MDD.")
        if article.format_size:
            add("format_size", "Seuls les produits finis ont un format.")

    # Règle 3 : durée de vie obligatoire, sauf pour les emballages
    if is_em and article.shelf_life_days:
        add("shelf_life_days", "Un emballage n'a pas de durée de vie.")
    if not is_em and not article.shelf_life_days:
        add("shelf_life_days", "La durée de vie (en jours) est obligatoire pour cet article.")

    # Codification (section 5)
    if is_pf:
        if article.recipe_id and article.format_size:
            article.code = build_finished_product_code(article)
    elif not article.code:
        add("code", "Le code est obligatoire.")
    elif is_mp:
        if article.category_id:
            expected = re.compile(rf"^MP-{re.escape(article.category.code)}-[A-Z0-9]+$")
            if not expected.match(article.code):
                add(
                    "code",
                    f"Le code d'une matière doit suivre le format "
                    f"MP-{article.category.code}-[CODE] (ex. MP-VIA-BOEUF15).",
                )
    elif article_type == ArticleType.SEMI_FINISHED:
        if not SEMI_FINISHED_CODE.match(article.code):
            add("code", "Le code d'un semi-fini doit suivre le format SF-[CODE] (ex. SF-SAUCEBOL).")
    elif is_em and not PACKAGING_CODE.match(article.code):
        add(
            "code",
            "Le code d'un emballage doit suivre le format EM-[TYPE]-[CODE] (ex. EM-BARQ-300N).",
        )

    if errors:
        raise ValidationError(errors)

    article.date_type = expected_date_type(article)
    article.storage_temperature_class = expected_temperature_class(article)


def expected_date_type(article) -> str:
    """Règle 3 : DDM pour les produits secs, DLC pour les produits frais."""
    if article.article_type == ArticleType.PACKAGING:
        return DateType.NONE
    if article.article_type == ArticleType.RAW_MATERIAL:
        return article.category.date_type
    # Plats cuisinés et semi-finis : produits frais
    return DateType.DLC


def expected_temperature_class(article) -> str:
    if article.article_type == ArticleType.RAW_MATERIAL:
        return article.category.temperature_class
    if article.article_type == ArticleType.PACKAGING:
        return TemperatureClass.AMBIENT
    return TemperatureClass.CHILLED


def validate_allergens(article, allergens) -> None:
    """Règle 8 : les allergènes se saisissent sur les matières premières.

    Ceux des recettes seront calculés à partir des nomenclatures (phase 5).
    """
    if allergens and article.article_type != ArticleType.RAW_MATERIAL:
        raise ValidationError(
            {
                "allergens": "Les allergènes se saisissent uniquement sur les matières "
                "premières : ceux des recettes sont calculés automatiquement."
            }
        )


# --- Nomenclatures ----------------------------------------------------------


def validate_bom(bom) -> None:
    if bom.article_id and bom.article.article_type not in (
        ArticleType.SEMI_FINISHED,
        ArticleType.FINISHED_PRODUCT,
    ):
        raise ValidationError(
            {"article": "Seuls les semi-finis et les produits finis ont une nomenclature."}
        )


def validate_bom_line(line) -> None:
    if not (line.bom_id and line.component_id):
        return
    component = line.component
    parent = line.bom.article
    errors: dict[str, str] = {}

    if component.article_type == ArticleType.FINISHED_PRODUCT:
        errors["component"] = "Un produit fini ne peut pas être utilisé comme composant."
    elif component.pk == parent.pk:
        errors["component"] = "Un article ne peut pas être son propre composant."
    elif bom_contains(component, parent):
        errors["component"] = (
            f"Boucle interdite : {component.code} contient déjà {parent.code} dans sa nomenclature."
        )

    if line.unit and line.unit != component.unit:
        errors["unit"] = (
            f"L'unité doit être celle de l'article {component.code} ({component.unit})."
        )

    if errors:
        raise ValidationError(errors)


def bom_contains(article, target, _seen: set[int] | None = None) -> bool:
    """Indique si `target` apparaît dans la nomenclature de `article`, à n'importe quel niveau."""
    seen = _seen if _seen is not None else set()
    if article.pk in seen or not hasattr(article, "bom"):
        return False
    seen.add(article.pk)
    for line in article.bom.lines.select_related("component"):
        if line.component_id == target.pk or bom_contains(line.component, target, seen):
            return True
    return False


def gross_quantity(line) -> Decimal:
    """Quantité à sortir du stock en tenant compte de la perte.

    Exemple : 40 kg de bœuf avec 25 % de perte à la cuisson → 53,333 kg bruts.
    """
    ratio = 1 - line.loss_rate / Decimal(100)
    return (line.quantity / ratio).quantize(Decimal("0.0001"))


# --- Sites, clients, fournisseurs -------------------------------------------


def validate_location(location) -> None:
    errors: dict[str, str] = {}
    if location.site_id and not location.code.startswith(f"{location.site.code}-"):
        errors["code"] = f"Le code doit commencer par le code du site ({location.site.code}-)."
    if (
        location.min_temperature is not None
        and location.max_temperature is not None
        and location.min_temperature > location.max_temperature
    ):
        errors["min_temperature"] = "La température minimale dépasse la température maximale."
    if errors:
        raise ValidationError(errors)


def validate_product_family(family) -> None:
    if family.site_id and family.site.site_type != SiteType.FACTORY:
        raise ValidationError({"site": "Une famille de produits est fabriquée dans une usine."})


def validate_customer(customer) -> None:
    if not (customer.sells_brand or customer.sells_private_label):
        raise ValidationError("Une enseigne doit vendre la marque Brévanne, du MDD, ou les deux.")
    if (
        customer.pk
        and not customer.sells_private_label
        and customer.private_label_articles.exists()
    ):
        raise ValidationError(
            {
                "sells_private_label": "Des produits finis MDD existent pour cette enseigne : "
                "désactive-les d'abord."
            }
        )


def validate_customer_warehouse(warehouse) -> None:
    if warehouse.customer_id and not warehouse.code.startswith(f"{warehouse.customer.code}-"):
        raise ValidationError(
            {
                "code": "Le code doit commencer par le code de l'enseigne "
                f"({warehouse.customer.code}-)."
            }
        )


def validate_supplier(supplier) -> None:
    if supplier.audited and not supplier.last_audit_date:
        raise ValidationError({"last_audit_date": "Indique la date du dernier audit."})


def validate_supplier_article(link) -> None:
    if not (link.supplier_id and link.article_id):
        return
    if link.article.article_type not in (ArticleType.RAW_MATERIAL, ArticleType.PACKAGING):
        raise ValidationError(
            {"article": "Un fournisseur livre uniquement des matières premières ou des emballages."}
        )
    if link.is_main_supplier:
        others = link.article.supplier_links.filter(is_main_supplier=True).exclude(pk=link.pk)
        if others.exists():
            raise ValidationError(
                {
                    "is_main_supplier": f"L'article {link.article.code} a déjà "
                    "un fournisseur principal."
                }
            )
