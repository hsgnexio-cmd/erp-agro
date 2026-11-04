"""Données de démonstration des achats : tarifs, commandes et réceptions.

Les dates sont calculées par rapport à aujourd'hui, pour que les contrôles de DLC
restent cohérents quel que soit le jour du chargement.
"""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from referentiel.models import Article, Location, Site, Supplier, SupplierArticle

from . import services
from .models import PurchaseOrder, SupplierPrice

# Prix HT en € par unité de stock (kg, litre ou unité)
RAW_MATERIAL_PRICES = {
    "BOEUF15": "7.80", "BOEUFBOUR": "9.20", "VEAU": "12.50", "LARDON": "6.40",
    "JAMBON": "7.10", "POULET": "8.30", "CREME35": "4.20", "LAIT": "0.95",
    "BEURRE": "7.60", "EMMENTAL": "6.90", "PARMESAN": "14.50", "MOZZA": "6.20",
    "OEUF": "2.80", "OIGNON": "0.90", "CAROTTE": "0.75", "CELERI": "1.10",
    "TOMATE": "1.60", "CHAMPI": "2.90", "POMTER": "0.55", "PERSIL": "6.00",
    "MENTHE": "8.00", "POIVRON": "2.40", "CONCOMB": "1.30", "AIL": "4.50",
    "PETPOIS": "1.70", "HARVERT": "1.90", "OIGSUR": "1.20", "PATLAS": "2.60",
    "PATCOQ": "1.40", "FARINE": "0.62", "SEMOULE": "1.10", "BOULGOUR": "1.50",
    "HUILOL": "6.80", "HUITOUR": "1.90", "SEL": "0.30", "POIVRE": "14.00",
    "CONCTOM": "2.20", "VINBLANC": "2.10", "VINROUGE": "2.30", "MOUTARDE": "3.10",
    "VINAIGRE": "1.20", "FONDVO": "9.50", "THON": "9.80", "SAUMON": "24.00",
    "CREVET": "13.50",
}  # fmt: skip
PACKAGING_PRICES = {
    "EM-BARQ-300N": "0.085", "EM-BARQ-1000N": "0.190", "EM-OPER-300": "0.021",
    "EM-OPER-1000": "0.034", "EM-POT-250": "0.070", "EM-POT-500": "0.095",
    "EM-COUV-POT": "0.030", "EM-CART-12": "0.420",
}  # fmt: skip
LABEL_PRICE = "0.012"

# Catégories aux prix hebdomadaires (fiche entreprise) ; les autres ont des prix annuels
WEEKLY_PRICE_CATEGORIES = {"VIA", "LEG", "LAI", "MER"}

# Commandes : (fournisseur, il y a N jours, [(article, quantité)], suite)
# suite : "brouillon", "envoyee", "annulee" ou une réception :
#   ("reception", il y a N jours, [(article, quantité, lot fournisseur, jours de DLC, température)])
ORDERS = [
    ("FOU-004", 12, [("MP-LAI-CREME35", "400"), ("MP-LAI-EMMENTAL", "150")],
     ("reception", 10, [("MP-LAI-CREME35", "400", "CB-0412", 19, "3.1"),
                        ("MP-LAI-EMMENTAL", "150", "CB-E-118", 40, "3.5")])),
    ("FOU-005", 9, [("MP-LAI-OEUF", "300")],
     # DLC trop courte : 6 jours restants sur 14 (43 % < 60 %) → lot bloqué
     ("reception", 8, [("MP-LAI-OEUF", "300", "OM-77120", 6, "3.0")])),
    ("FOU-008", 8, [("MP-SUR-PETPOIS", "400")],
     ("reception", 6, [("MP-SUR-PETPOIS", "400", "SA-PP-2291", 500, "-20.0")])),
    ("FOU-011", 7, [("MP-MER-THON", "120")], "annulee"),
    ("FOU-013", 6, [("EM-BARQ-300N", "20000"), ("EM-POT-500", "5000")], "envoyee"),
    ("FOU-004", 5, [("MP-LAI-CREME35", "350"), ("MP-LAI-PARMESAN", "40")],
     ("reception", 3, [("MP-LAI-CREME35", "350", "CB-0419", 20, "2.8"),
                       ("MP-LAI-PARMESAN", "40", "CB-P-077", 55, "3.0")])),
    ("FOU-001", 4, [("MP-VIA-BOEUF15", "600"), ("MP-VIA-VEAU", "250")],
     # Température de 6,5 °C sur le bœuf → lot bloqué (règle 7)
     ("reception", 2, [("MP-VIA-BOEUF15", "600", "VO-26-3321", 6, "6.5"),
                       ("MP-VIA-VEAU", "250", "VO-26-3322", 6, "2.9")])),
    ("FOU-003", 3, [("MP-LAI-LAIT", "2000"), ("MP-LAI-BEURRE", "120")],
     # Le beurre n'est pas encore livré → commande partiellement reçue
     ("reception", 1, [("MP-LAI-LAIT", "2000", "LM-5541", 9, "3.2")])),
    ("FOU-009", 2, [("MP-SEC-PATLAS", "800"), ("MP-SEC-FARINE", "1500")], "envoyee"),
    ("FOU-006", 0, [("MP-LEG-TOMATE", "500"), ("MP-LEG-OIGNON", "300")], "brouillon"),
]  # fmt: skip


def _price_for(article: Article) -> Decimal:
    if article.code.startswith("EM-ETIQ-"):
        return Decimal(LABEL_PRICE)
    if article.code in PACKAGING_PRICES:
        return Decimal(PACKAGING_PRICES[article.code])
    return Decimal(RAW_MATERIAL_PRICES.get(article.code.rsplit("-", 1)[-1], "1.00"))


def _load_prices(today) -> int:
    one_year_ago = today - timedelta(days=365)
    monday = today - timedelta(days=today.weekday())
    count = 0
    for link in SupplierArticle.objects.select_related("article__category"):
        price = _price_for(link.article)
        category = link.article.category.code if link.article.category_id else None
        if category in WEEKLY_PRICE_CATEGORIES:
            # Prix de la semaine en cours, et ancien prix jusqu'à dimanche dernier
            SupplierPrice.objects.update_or_create(
                supplier_article=link,
                valid_from=one_year_ago,
                defaults={
                    "unit_price": (price * Decimal("0.97")).quantize(Decimal("0.0001")),
                    "valid_to": monday - timedelta(days=1),
                },
            )
            SupplierPrice.objects.update_or_create(
                supplier_article=link, valid_from=monday, defaults={"unit_price": price}
            )
        else:
            SupplierPrice.objects.update_or_create(
                supplier_article=link, valid_from=one_year_ago, defaults={"unit_price": price}
            )
        count += 1
    return count


def _at(day, hour: int = 7, minute: int = 30) -> datetime:
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


@transaction.atomic
def load_demo_data() -> dict[str, int | str]:
    today = timezone.localdate()
    counts: dict[str, int | str] = {"tarifs": _load_prices(today)}

    if PurchaseOrder.objects.exists():
        counts["commandes"] = "déjà présentes, non modifiées"
        return counts

    warehouse = Site.objects.get(code="MPE")
    # Zone de quarantaine adaptée à la température de conservation des produits reçus
    quarantine_by_class = {
        location.temperature_class: location
        for location in Location.objects.filter(code__startswith="MPE-QUAR")
    }
    articles = {a.code: a for a in Article.objects.filter(article_type__in=["MP", "EM"])}

    for supplier_code, days_ago, lines, follow_up in ORDERS:
        order = services.create_purchase_order(
            supplier=Supplier.objects.get(code=supplier_code),
            delivery_site=warehouse,
            order_date=today - timedelta(days=days_ago),
            lines=[{"article": articles[code], "quantity": Decimal(qty)} for code, qty in lines],
        )
        if follow_up == "brouillon":
            continue
        services.send_order(order)
        if follow_up == "annulee":
            services.cancel_order(order)
        elif isinstance(follow_up, tuple):
            _, received_days_ago, received = follow_up
            reception_day = today - timedelta(days=received_days_ago)
            order_lines = {line.article.code: line for line in order.lines.all()}
            first_article = articles[received[0][0]]
            services.create_reception(
                order=order,
                location=quarantine_by_class[first_article.storage_temperature_class],
                delivery_note_number=f"BL-{supplier_code[-3:]}-{reception_day:%m%d}",
                received_at=_at(reception_day),
                lines=[
                    {
                        "order_line": order_lines[code],
                        "quantity": Decimal(qty),
                        "supplier_lot_number": supplier_lot,
                        "expiry_date": reception_day + timedelta(days=shelf_days),
                        "temperature": Decimal(temperature),
                        "appearance_ok": True,
                    }
                    for code, qty, supplier_lot, shelf_days, temperature in received
                ],
            )

    counts["commandes"] = PurchaseOrder.objects.count()
    counts["réceptions"] = sum(1 for o in ORDERS if isinstance(o[3], tuple))
    return counts
