"""Recherche globale (barre du haut, Ctrl+K) : lots, articles, enseignes, fournisseurs, OF.

Chaque famille de résultats respecte la matrice d'accès en lecture (comptes/access.py) : un
rôle qui ne voit pas la production ne reçoit aucun ordre de fabrication.
"""

from django.db.models import Q

from comptes.access import can_read
from production.models import ProductionOrder
from referentiel.models import Article, Customer, Supplier
from stocks.models import Lot

MIN_LENGTH = 2
LIMIT = 5


def search(user, query: str) -> list[dict]:
    """Jusqu'à 5 résultats par famille ; `url` est l'adresse de l'écran dans l'application."""
    query = query.strip()
    if len(query) < MIN_LENGTH:
        return []
    results: list[dict] = []

    def add(kind: str, label: str, detail: str, url: str) -> None:
        results.append({"type": kind, "label": label, "detail": detail, "url": url})

    if can_read(user, "stocks"):
        lots = Lot.objects.filter(
            Q(number__icontains=query) | Q(supplier_lot_number__icontains=query)
        ).select_related("article")
        for lot in lots.order_by("-created_at")[:LIMIT]:
            add("lot", lot.number, f"{lot.article.code} – {lot.article.name}", f"/lots/{lot.pk}")
    if can_read(user, "referentiel"):
        articles = Article.objects.filter(Q(code__icontains=query) | Q(name__icontains=query))
        for article in articles.order_by("code")[:LIMIT]:
            add("article", article.code, article.name, f"/articles/{article.pk}")
        customers = Customer.objects.filter(Q(code__icontains=query) | Q(name__icontains=query))
        for customer in customers.order_by("code")[:LIMIT]:
            add("client", customer.code, customer.name, "/clients")
        suppliers = Supplier.objects.filter(Q(code__icontains=query) | Q(name__icontains=query))
        for supplier in suppliers.order_by("code")[:LIMIT]:
            add("fournisseur", supplier.code, supplier.name, "/fournisseurs")
    if can_read(user, "production"):
        orders = ProductionOrder.objects.filter(number__icontains=query).select_related("article")
        for order in orders.order_by("-planned_date", "-number")[:LIMIT]:
            add("of", order.number, f"{order.article.code} – {order.article.name}",
                f"/production/{order.pk}")  # fmt: skip
    return results
