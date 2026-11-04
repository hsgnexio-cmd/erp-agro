"""Données fictives de démonstration, cohérentes avec docs/fiche-entreprise.md.

Chargement : python manage.py charger_donnees_demo
Le chargement peut être relancé sans créer de doublons.
"""

from datetime import date
from decimal import Decimal

from django.db import transaction

from .choices import ArticleType, CustomerType, DateType, SiteType, TemperatureClass, Unit
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
    Recipe,
    Site,
    Supplier,
    SupplierArticle,
)

AMB, FP, FN = TemperatureClass.AMBIENT, TemperatureClass.CHILLED, TemperatureClass.FROZEN

SITES = [
    ("NAN", "Usine plats chauds", SiteType.FACTORY, "Nantes"),
    ("REN", "Usine traiteur froid", SiteType.FACTORY, "Rennes"),
    ("PFN", "Plateforme produits finis", SiteType.PLATFORM, "Nantes"),
    ("MPE", "Entrepôt matières et emballages", SiteType.WAREHOUSE, "Nantes"),
]

# (site, code, nom, classe, mini, maxi)
LOCATIONS = [
    ("MPE", "MPE-AMB-01", "Magasin matières ambiant", AMB, "15", "25"),
    ("MPE", "MPE-EMB-01", "Magasin emballages", AMB, "10", "30"),
    ("MPE", "MPE-FP-01", "Chambre froide matières", FP, "0", "4"),
    ("MPE", "MPE-FN-01", "Chambre froide négative", FN, "-25", "-18"),
    ("MPE", "MPE-QUAR", "Zone de quarantaine réception", FP, "0", "4"),
    ("NAN", "NAN-CF-MP", "Chambre froide matières atelier", FP, "0", "4"),
    ("NAN", "NAN-CF-SF", "Chambre froide semi-finis", FP, "0", "4"),
    ("REN", "REN-CF-MP", "Chambre froide matières atelier", FP, "0", "4"),
    ("REN", "REN-CF-SF", "Chambre froide semi-finis", FP, "0", "4"),
    ("PFN", "PFN-FRAIS-A", "Stock produits finis – allée A", FP, "0", "4"),
    ("PFN", "PFN-FRAIS-B", "Stock produits finis – allée B", FP, "0", "4"),
    ("PFN", "PFN-QUAR", "Quarantaine produits finis", FP, "0", "4"),
    ("PFN", "PFN-QUAI", "Quai d'expédition", FP, "0", "4"),
    ("PFN", "PFN-RETOUR", "Zone retours et invendables", FP, "0", "4"),
]

# (code, nom, usine, DLC moyenne en jours)
FAMILIES = [
    ("PAT", "Plats à base de pâtes", "NAN", 14),
    ("GRA", "Gratins et hachis", "NAN", 12),
    ("SAU", "Plats en sauce", "NAN", 16),
    ("SAL", "Salades composées", "REN", 10),
    ("TAB", "Taboulés et céréales", "REN", 12),
    ("ENT", "Entrées et snacking", "REN", 8),
]

CATEGORIES = [
    ("VIA", "Viandes et volailles", FP, DateType.DLC),
    ("LAI", "Produits laitiers et œufs", FP, DateType.DLC),
    ("LEG", "Légumes frais", FP, DateType.DLC),
    ("SUR", "Légumes surgelés", FN, DateType.DDM),
    ("SEC", "Produits secs", AMB, DateType.DDM),
    ("MER", "Produits de la mer", FP, DateType.DLC),
]

# (code, nom, type, marque Brévanne, MDD, DLC mini %, nombre d'entrepôts)
CUSTOMERS = [
    ("ENS1", "Hyper Atlantique", CustomerType.HYPERMARKET, True, True, "70", 9),
    ("ENS2", "Marché Plus", CustomerType.HYPER_SUPER, True, True, "70", 11),
    ("ENS3", "Coopérative Ouest", CustomerType.INDEPENDENT, True, True, "65", 8),
    ("ENS4", "Proxi Ville", CustomerType.CONVENIENCE, True, False, "75", 6),
    ("ENS5", "Prix Malin", CustomerType.DISCOUNT, False, True, "60", 7),
    ("ENS6", "Bio Nature", CustomerType.ORGANIC, False, True, "70", 4),
]

WAREHOUSE_CITIES = [
    ("Nantes", "44000"),
    ("Rennes", "35000"),
    ("Angers", "49000"),
    ("Le Mans", "72000"),
    ("Brest", "29200"),
    ("Vannes", "56000"),
    ("Tours", "37000"),
    ("Poitiers", "86000"),
    ("La Rochelle", "17000"),
    ("Caen", "14000"),
    ("Lorient", "56100"),
    ("Saint-Brieuc", "22000"),
]

# (code, nom, ville, délai jours, catégories, audité)
SUPPLIERS = [
    ("FOU-001", "Viandes de l'Ouest", "Cholet", 2, ["VIA"], True),
    ("FOU-002", "Volailles du Bocage", "Bressuire", 3, ["VIA"], True),
    ("FOU-003", "Laiterie de la Mée", "Châteaubriant", 3, ["LAI"], True),
    ("FOU-004", "Crèmerie Bretonne", "Vitré", 3, ["LAI"], True),
    ("FOU-005", "Ovoproduits du Maine", "Laval", 3, ["LAI"], True),
    ("FOU-006", "Maraîchers Nantais", "Saint-Julien-de-Concelles", 1, ["LEG"], True),
    ("FOU-007", "Légumes du Val de Loire", "Saumur", 2, ["LEG"], False),
    ("FOU-008", "Surgelés Atlantique", "Saint-Nazaire", 7, ["SUR"], True),
    ("FOU-009", "Moulins de Brocéliande", "Ploërmel", 10, ["SEC"], True),
    ("FOU-010", "Épicerie Ligérienne", "Ancenis", 12, ["SEC"], True),
    ("FOU-011", "Marée de Concarneau", "Concarneau", 4, ["MER"], True),
    ("FOU-012", "Emballages Armor", "Lamballe", 30, [], True),
    ("FOU-013", "Plastiques de l'Erdre", "Nort-sur-Erdre", 35, [], True),
    ("FOU-014", "Étiquettes Océane", "Pornic", 21, [], True),
    ("FOU-015", "Salaisons de Vendée", "La Roche-sur-Yon", 3, ["VIA"], True),
]

# Matières premières :
# (catégorie, code, nom, unité, durée de vie, allergènes, fournisseur principal)
RAW_MATERIALS = [
    ("VIA", "BOEUF15", "Bœuf haché 15 % MG", Unit.KG, 6, [], "FOU-001"),
    ("VIA", "BOEUFBOUR", "Bœuf à braiser (paleron)", Unit.KG, 8, [], "FOU-001"),
    ("VIA", "VEAU", "Veau pour blanquette", Unit.KG, 7, [], "FOU-001"),
    ("VIA", "LARDON", "Lardons fumés", Unit.KG, 21, [], "FOU-015"),
    ("VIA", "JAMBON", "Dés de jambon cuit", Unit.KG, 14, [], "FOU-015"),
    ("VIA", "POULET", "Filet de poulet", Unit.KG, 6, [], "FOU-002"),
    ("LAI", "CREME35", "Crème fraîche 35 % MG", Unit.KG, 21, ["lait"], "FOU-004"),
    ("LAI", "LAIT", "Lait entier", Unit.LITRE, 10, ["lait"], "FOU-003"),
    ("LAI", "BEURRE", "Beurre doux", Unit.KG, 60, ["lait"], "FOU-003"),
    ("LAI", "EMMENTAL", "Emmental râpé", Unit.KG, 45, ["lait"], "FOU-004"),
    ("LAI", "PARMESAN", "Parmesan râpé", Unit.KG, 60, ["lait"], "FOU-004"),
    ("LAI", "MOZZA", "Mozzarella", Unit.KG, 21, ["lait"], "FOU-003"),
    ("LAI", "OEUF", "Œufs entiers liquides pasteurisés", Unit.KG, 14, ["oeufs"], "FOU-005"),
    ("LEG", "OIGNON", "Oignons émincés", Unit.KG, 7, [], "FOU-006"),
    ("LEG", "CAROTTE", "Carottes", Unit.KG, 14, [], "FOU-006"),
    ("LEG", "CELERI", "Céleri-rave", Unit.KG, 14, ["celeri"], "FOU-007"),
    ("LEG", "TOMATE", "Tomates", Unit.KG, 7, [], "FOU-006"),
    ("LEG", "CHAMPI", "Champignons de Paris", Unit.KG, 5, [], "FOU-007"),
    ("LEG", "POMTER", "Pommes de terre", Unit.KG, 30, [], "FOU-007"),
    ("LEG", "PERSIL", "Persil frais", Unit.KG, 5, [], "FOU-006"),
    ("LEG", "MENTHE", "Menthe fraîche", Unit.KG, 5, [], "FOU-006"),
    ("LEG", "POIVRON", "Poivrons", Unit.KG, 7, [], "FOU-006"),
    ("LEG", "CONCOMB", "Concombres", Unit.KG, 7, [], "FOU-006"),
    ("LEG", "AIL", "Ail", Unit.KG, 30, [], "FOU-007"),
    ("SUR", "PETPOIS", "Petits pois surgelés", Unit.KG, 540, [], "FOU-008"),
    ("SUR", "HARVERT", "Haricots verts surgelés", Unit.KG, 540, [], "FOU-008"),
    ("SUR", "OIGSUR", "Oignons surgelés", Unit.KG, 540, [], "FOU-008"),
    ("SEC", "PATLAS", "Feuilles de lasagne aux œufs", Unit.KG, 365, ["gluten", "oeufs"], "FOU-009"),
    ("SEC", "PATCOQ", "Coquillettes", Unit.KG, 540, ["gluten"], "FOU-009"),
    ("SEC", "FARINE", "Farine de blé T55", Unit.KG, 365, ["gluten"], "FOU-009"),
    ("SEC", "SEMOULE", "Semoule de blé dur", Unit.KG, 365, ["gluten"], "FOU-009"),
    ("SEC", "BOULGOUR", "Boulgour", Unit.KG, 365, ["gluten"], "FOU-009"),
    ("SEC", "HUILOL", "Huile d'olive", Unit.LITRE, 540, [], "FOU-010"),
    ("SEC", "HUITOUR", "Huile de tournesol", Unit.LITRE, 540, [], "FOU-010"),
    ("SEC", "SEL", "Sel fin", Unit.KG, 1095, [], "FOU-010"),
    ("SEC", "POIVRE", "Poivre noir moulu", Unit.KG, 730, [], "FOU-010"),
    ("SEC", "CONCTOM", "Concentré de tomate", Unit.KG, 730, [], "FOU-010"),
    ("SEC", "VINBLANC", "Vin blanc de cuisine", Unit.LITRE, 365, ["sulfites"], "FOU-010"),
    ("SEC", "VINROUGE", "Vin rouge de cuisine", Unit.LITRE, 365, ["sulfites"], "FOU-010"),
    ("SEC", "MOUTARDE", "Moutarde de Dijon", Unit.KG, 365, ["moutarde"], "FOU-010"),
    ("SEC", "VINAIGRE", "Vinaigre de vin", Unit.LITRE, 730, ["sulfites"], "FOU-010"),
    ("SEC", "FONDVO", "Fond de veau déshydraté", Unit.KG, 540, ["gluten", "celeri"], "FOU-010"),
    ("MER", "THON", "Miettes de thon", Unit.KG, 10, ["poissons"], "FOU-011"),
    ("MER", "SAUMON", "Saumon fumé", Unit.KG, 21, ["poissons"], "FOU-011"),
    ("MER", "CREVET", "Crevettes cuites décortiquées", Unit.KG, 7, ["crustaces"], "FOU-011"),
]

# Emballages : (code, nom, fournisseur principal)
PACKAGING = [
    ("EM-BARQ-300N", "Barquette noire 300 g", "FOU-013"),
    ("EM-BARQ-1000N", "Barquette familiale noire 1 kg", "FOU-013"),
    ("EM-OPER-300", "Opercule barquette 300 g", "FOU-012"),
    ("EM-OPER-1000", "Opercule barquette 1 kg", "FOU-012"),
    ("EM-POT-250", "Pot traiteur 250 g", "FOU-013"),
    ("EM-POT-500", "Pot traiteur 500 g", "FOU-013"),
    ("EM-COUV-POT", "Couvercle pot traiteur", "FOU-013"),
    ("EM-CART-12", "Carton de 12 unités", "FOU-012"),
    ("EM-ETIQ-BRE", "Étiquette marque Brévanne", "FOU-014"),
    ("EM-ETIQ-ENS1", "Étiquette MDD Hyper Atlantique", "FOU-014"),
    ("EM-ETIQ-ENS2", "Étiquette MDD Marché Plus", "FOU-014"),
    ("EM-ETIQ-ENS3", "Étiquette MDD Coopérative Ouest", "FOU-014"),
    ("EM-ETIQ-ENS5", "Étiquette MDD Prix Malin", "FOU-014"),
    ("EM-ETIQ-ENS6", "Étiquette MDD Bio Nature", "FOU-014"),
]

# Semi-finis : (code, nom, durée de vie, quantité de base en kg, lignes)
# Ligne : (composant, quantité, taux de perte %)
SEMI_FINISHED = [
    (
        "SF-SAUCEBOL",
        "Sauce bolognaise",
        3,
        "100",
        [
            ("MP-VIA-BOEUF15", "40", "25"),
            ("MP-LEG-TOMATE", "30", "5"),
            ("MP-SEC-CONCTOM", "8", "0"),
            ("MP-LEG-OIGNON", "10", "10"),
            ("MP-LEG-CAROTTE", "6", "10"),
            ("MP-SEC-HUILOL", "2", "0"),
            ("MP-SEC-VINROUGE", "4", "0"),
            ("MP-SEC-SEL", "0.8", "0"),
            ("MP-SEC-POIVRE", "0.2", "0"),
        ],
    ),
    (
        "SF-BECHAMEL",
        "Sauce béchamel à la crème",
        3,
        "100",
        [
            ("MP-LAI-LAIT", "70", "0"),
            ("MP-LAI-CREME35", "10", "0"),
            ("MP-LAI-BEURRE", "8", "0"),
            ("MP-SEC-FARINE", "8", "0"),
            ("MP-SEC-SEL", "0.6", "0"),
        ],
    ),
    (
        "SF-PUREE",
        "Purée de pommes de terre",
        3,
        "100",
        [
            ("MP-LEG-POMTER", "85", "15"),
            ("MP-LAI-LAIT", "10", "0"),
            ("MP-LAI-BEURRE", "4", "0"),
            ("MP-LAI-CREME35", "3", "0"),
            ("MP-SEC-SEL", "0.6", "0"),
        ],
    ),
    (
        "SF-VINAIG",
        "Vinaigrette moutardée",
        5,
        "100",
        [
            ("MP-SEC-HUITOUR", "60", "0"),
            ("MP-SEC-VINAIGRE", "25", "0"),
            ("MP-SEC-MOUTARDE", "12", "0"),
            ("MP-SEC-SEL", "2", "0"),
            ("MP-SEC-POIVRE", "1", "0"),
        ],
    ),
    (
        "SF-REMOUL",
        "Sauce rémoulade",
        4,
        "100",
        [
            ("MP-SEC-HUITOUR", "70", "0"),
            ("MP-LAI-OEUF", "10", "0"),
            ("MP-SEC-MOUTARDE", "10", "0"),
            ("MP-SEC-VINAIGRE", "5", "0"),
            ("MP-LAI-CREME35", "4", "0"),
            ("MP-SEC-SEL", "1", "0"),
        ],
    ),
]

RECIPES = [
    ("LASBOL", "Lasagnes bolognaise", "PAT"),
    ("COQJAM", "Gratin de coquillettes au jambon", "PAT"),
    ("HACHIS", "Hachis parmentier", "GRA"),
    ("GRADAU", "Gratin dauphinois", "GRA"),
    ("BOEBOU", "Bœuf bourguignon", "SAU"),
    ("BLANQ", "Blanquette de veau", "SAU"),
    ("PIEMON", "Salade piémontaise", "SAL"),
    ("SALPAT", "Salade de pâtes au thon", "SAL"),
    ("TABOR", "Taboulé oriental", "TAB"),
    ("CARAP", "Carottes râpées", "ENT"),
    ("CELREM", "Céleri rémoulade", "ENT"),
]

# Ingrédients d'une recette pour 1 kg de produit fini : (composant, kg, perte %)
RECIPE_INGREDIENTS_PER_KG = {
    "LASBOL": [
        ("SF-SAUCEBOL", "0.400", "0"),
        ("SF-BECHAMEL", "0.300", "0"),
        ("MP-SEC-PATLAS", "0.200", "0"),
        ("MP-LAI-EMMENTAL", "0.100", "0"),
    ],
    "COQJAM": [
        ("MP-SEC-PATCOQ", "0.300", "0"),
        ("SF-BECHAMEL", "0.400", "0"),
        ("MP-VIA-JAMBON", "0.200", "0"),
        ("MP-LAI-EMMENTAL", "0.100", "0"),
    ],
    "HACHIS": [
        ("SF-PUREE", "0.560", "0"),
        ("MP-VIA-BOEUF15", "0.370", "25"),
        ("MP-LEG-OIGNON", "0.060", "10"),
        ("MP-LAI-EMMENTAL", "0.050", "0"),
    ],
    "GRADAU": [
        ("MP-LEG-POMTER", "0.640", "10"),
        ("MP-LAI-CREME35", "0.200", "0"),
        ("MP-LAI-LAIT", "0.150", "0"),
        ("MP-LEG-AIL", "0.005", "0"),
        ("MP-SEC-SEL", "0.008", "0"),
    ],
    "BOEBOU": [
        ("MP-VIA-BOEUFBOUR", "0.500", "30"),
        ("MP-SEC-VINROUGE", "0.200", "0"),
        ("MP-LEG-CAROTTE", "0.130", "10"),
        ("MP-LEG-CHAMPI", "0.100", "5"),
        ("MP-VIA-LARDON", "0.070", "0"),
        ("MP-SEC-FONDVO", "0.030", "0"),
    ],
    "BLANQ": [
        ("MP-VIA-VEAU", "0.470", "25"),
        ("MP-LAI-CREME35", "0.170", "0"),
        ("MP-LEG-CHAMPI", "0.130", "5"),
        ("MP-LEG-CAROTTE", "0.100", "10"),
        ("MP-SEC-FONDVO", "0.030", "0"),
        ("MP-SEC-FARINE", "0.030", "0"),
    ],
    "PIEMON": [
        ("MP-LEG-POMTER", "0.570", "10"),
        ("SF-REMOUL", "0.130", "0"),
        ("MP-LAI-OEUF", "0.100", "0"),
        ("MP-VIA-JAMBON", "0.100", "0"),
        ("MP-LEG-TOMATE", "0.100", "5"),
    ],
    "SALPAT": [
        ("MP-SEC-PATCOQ", "0.400", "0"),
        ("MP-MER-THON", "0.200", "0"),
        ("MP-LEG-TOMATE", "0.130", "5"),
        ("MP-LEG-POIVRON", "0.100", "10"),
        ("SF-VINAIG", "0.100", "0"),
    ],
    "TABOR": [
        ("MP-SEC-SEMOULE", "0.400", "0"),
        ("MP-LEG-TOMATE", "0.200", "5"),
        ("MP-LEG-CONCOMB", "0.120", "10"),
        ("MP-LEG-POIVRON", "0.100", "10"),
        ("MP-SEC-HUILOL", "0.050", "0"),
        ("MP-LEG-MENTHE", "0.010", "0"),
        ("MP-LEG-PERSIL", "0.010", "0"),
        ("MP-SEC-SEL", "0.008", "0"),
    ],
    "CARAP": [
        ("MP-LEG-CAROTTE", "0.880", "10"),
        ("SF-VINAIG", "0.120", "0"),
    ],
    "CELREM": [
        ("MP-LEG-CELERI", "0.800", "15"),
        ("SF-REMOUL", "0.200", "0"),
    ],
}

# Produits finis : (recette, enseigne MDD ou None pour Brévanne, format en g)
FINISHED_PRODUCTS = [
    ("LASBOL", None, 300),
    ("LASBOL", None, 1000),
    ("LASBOL", "ENS1", 300),
    ("LASBOL", "ENS2", 1000),
    ("COQJAM", None, 300),
    ("COQJAM", "ENS3", 300),
    ("HACHIS", None, 300),
    ("HACHIS", None, 1000),
    ("HACHIS", "ENS5", 300),
    ("GRADAU", None, 1000),
    ("BOEBOU", None, 300),
    ("BOEBOU", "ENS2", 300),
    ("BLANQ", None, 300),
    ("BLANQ", "ENS3", 300),
    ("PIEMON", None, 300),
    ("PIEMON", "ENS6", 300),
    ("SALPAT", None, 300),
    ("TABOR", None, 500),
    ("TABOR", "ENS5", 500),
    ("CARAP", None, 250),
    ("CELREM", None, 250),
    ("CELREM", "ENS2", 250),
]

# Emballages selon le format
PACKAGING_BY_FORMAT = {
    250: ["EM-POT-250", "EM-COUV-POT"],
    300: ["EM-BARQ-300N", "EM-OPER-300"],
    500: ["EM-POT-500", "EM-COUV-POT"],
    1000: ["EM-BARQ-1000N", "EM-OPER-1000"],
}

FINISHED_PRODUCT_NAMES = {
    None: "Brévanne",
    "ENS1": "MDD Hyper Atlantique",
    "ENS2": "MDD Marché Plus",
    "ENS3": "MDD Coopérative Ouest",
    "ENS5": "MDD Prix Malin",
    "ENS6": "MDD Bio Nature",
}


def _format_label(grams: int) -> str:
    return "1 kg" if grams == 1000 else f"{grams} g"


@transaction.atomic
def load_demo_data() -> dict[str, int]:
    """Crée ou met à jour toutes les données de démonstration."""
    sites = {}
    for code, name, site_type, city in SITES:
        sites[code], _ = Site.objects.update_or_create(
            code=code, defaults={"name": name, "site_type": site_type, "city": city}
        )

    for site_code, code, name, temp_class, t_min, t_max in LOCATIONS:
        Location.objects.update_or_create(
            code=code,
            defaults={
                "site": sites[site_code],
                "name": name,
                "temperature_class": temp_class,
                "min_temperature": Decimal(t_min),
                "max_temperature": Decimal(t_max),
            },
        )

    families = {}
    family_shelf_life = {}
    for code, name, site_code, shelf_life in FAMILIES:
        families[code], _ = ProductFamily.objects.update_or_create(
            code=code, defaults={"name": name, "site": sites[site_code]}
        )
        family_shelf_life[code] = shelf_life

    categories = {}
    for code, name, temp_class, date_type in CATEGORIES:
        categories[code], _ = MaterialCategory.objects.update_or_create(
            code=code,
            defaults={"name": name, "temperature_class": temp_class, "date_type": date_type},
        )

    customers = {}
    for code, name, ctype, brand, mdd, pct, warehouse_count in CUSTOMERS:
        customers[code], _ = Customer.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "customer_type": ctype,
                "sells_brand": brand,
                "sells_private_label": mdd,
                "min_remaining_shelf_life_pct": Decimal(pct),
            },
        )
        for index in range(warehouse_count):
            city, postal_code = WAREHOUSE_CITIES[(index + int(code[3:])) % len(WAREHOUSE_CITIES)]
            CustomerWarehouse.objects.update_or_create(
                code=f"{code}-E{index + 1:02d}",
                defaults={
                    "customer": customers[code],
                    "name": f"Entrepôt {name} {city}",
                    "postal_code": postal_code,
                    "city": city,
                },
            )

    suppliers = {}
    for code, name, city, lead_time, cat_codes, audited in SUPPLIERS:
        suppliers[code], _ = Supplier.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "city": city,
                "lead_time_days": lead_time,
                "audited": audited,
                "last_audit_date": date(2026, 3, 15) if audited else None,
            },
        )
        suppliers[code].categories.set([categories[c] for c in cat_codes])

    allergens = {a.code: a for a in Allergen.objects.all()}
    articles = {}

    for cat_code, suffix, name, unit, shelf_life, allergen_codes, supplier in RAW_MATERIALS:
        code = f"MP-{cat_code}-{suffix}"
        article, _ = Article.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "article_type": ArticleType.RAW_MATERIAL,
                "unit": unit,
                "category": categories[cat_code],
                "shelf_life_days": shelf_life,
            },
        )
        article.allergens.set([allergens[c] for c in allergen_codes])
        articles[code] = article
        _link_supplier(suppliers[supplier], article)

    for code, name, supplier in PACKAGING:
        articles[code], _ = Article.objects.update_or_create(
            code=code,
            defaults={"name": name, "article_type": ArticleType.PACKAGING, "unit": Unit.UNIT},
        )
        _link_supplier(suppliers[supplier], articles[code])

    for code, name, shelf_life, base_quantity, lines in SEMI_FINISHED:
        articles[code], _ = Article.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "article_type": ArticleType.SEMI_FINISHED,
                "unit": Unit.KG,
                "shelf_life_days": shelf_life,
            },
        )
        _save_bom(articles[code], Decimal(base_quantity), lines, articles)

    recipes = {}
    for code, name, family_code in RECIPES:
        recipes[code], _ = Recipe.objects.update_or_create(
            code=code, defaults={"name": name, "family": families[family_code]}
        )

    finished_count = 0
    for recipe_code, customer_code, grams in FINISHED_PRODUCTS:
        recipe = recipes[recipe_code]
        customer = customers[customer_code] if customer_code else None
        article, _ = Article.objects.update_or_create(
            recipe=recipe,
            brand_customer=customer,
            format_size=grams,
            defaults={
                "name": f"{recipe.name} {_format_label(grams)} – "
                f"{FINISHED_PRODUCT_NAMES[customer_code]}",
                "article_type": ArticleType.FINISHED_PRODUCT,
                "unit": Unit.UNIT,
                "shelf_life_days": family_shelf_life[recipe.family.code],
            },
        )
        kg = Decimal(grams) / Decimal(1000)
        label = f"EM-ETIQ-{customer_code or 'BRE'}"
        lines = [
            (component, str((Decimal(qty) * kg).quantize(Decimal("0.0001"))), loss)
            for component, qty, loss in RECIPE_INGREDIENTS_PER_KG[recipe_code]
        ]
        lines += [(em, "1", "0") for em in PACKAGING_BY_FORMAT[grams]]
        lines += [(label, "1", "0"), ("EM-CART-12", "0.0834", "0")]
        _save_bom(article, Decimal("1"), lines, articles)
        finished_count += 1

    return {
        "sites": len(sites),
        "emplacements": Location.objects.count(),
        "enseignes": len(customers),
        "entrepôts clients": CustomerWarehouse.objects.count(),
        "fournisseurs": len(suppliers),
        "matières premières": len(RAW_MATERIALS),
        "emballages": len(PACKAGING),
        "semi-finis": len(SEMI_FINISHED),
        "recettes": len(recipes),
        "produits finis": finished_count,
    }


def _link_supplier(supplier: Supplier, article: Article) -> None:
    SupplierArticle.objects.update_or_create(
        supplier=supplier, article=article, defaults={"is_main_supplier": True}
    )


def _save_bom(article: Article, base_quantity: Decimal, lines, articles: dict) -> None:
    bom, _ = BillOfMaterials.objects.update_or_create(
        article=article, defaults={"base_quantity": base_quantity}
    )
    for component_code, quantity, loss_rate in lines:
        component = articles[component_code]
        BOMLine.objects.update_or_create(
            bom=bom,
            component=component,
            defaults={
                "quantity": Decimal(quantity),
                "unit": component.unit,
                "loss_rate": Decimal(loss_rate),
            },
        )
