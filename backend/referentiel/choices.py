"""Listes de valeurs autorisées du référentiel."""

from django.db import models


class SiteType(models.TextChoices):
    FACTORY = "usine", "Usine"
    PLATFORM = "plateforme", "Plateforme produits finis"
    WAREHOUSE = "entrepot", "Entrepôt matières et emballages"


class TemperatureClass(models.TextChoices):
    AMBIENT = "ambiant", "Ambiant"
    CHILLED = "froid_positif", "Froid positif (0 à 4 °C)"
    FROZEN = "froid_negatif", "Froid négatif (-18 °C)"


class DateType(models.TextChoices):
    # Règle 3 : DLC pour les produits frais, DDM pour les produits secs
    DLC = "DLC", "DLC (date limite de consommation)"
    DDM = "DDM", "DDM (date de durabilité minimale)"
    NONE = "aucune", "Aucune"


class Unit(models.TextChoices):
    KG = "kg", "kilogramme"
    LITRE = "l", "litre"
    UNIT = "u", "unité"


class ArticleType(models.TextChoices):
    RAW_MATERIAL = "MP", "Matière première"
    SEMI_FINISHED = "SF", "Semi-fini"
    FINISHED_PRODUCT = "PF", "Produit fini"
    PACKAGING = "EM", "Emballage"


class CustomerType(models.TextChoices):
    HYPERMARKET = "hyper", "Hypermarchés"
    HYPER_SUPER = "hyper_super", "Hyper et supermarchés"
    INDEPENDENT = "independants", "Indépendants"
    CONVENIENCE = "proximite", "Proximité"
    DISCOUNT = "discount", "Discount"
    ORGANIC = "bio", "Bio"
