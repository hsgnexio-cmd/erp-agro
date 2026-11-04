"""Données de démonstration des ventes : tarifs, commandes EDI récentes, saisie manuelle."""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from referentiel.models import Article, Customer

from . import edi, orders
from .models import CustomerOrder, SalePrice

# Prix HT de base d'une unité selon le format (g) ; les MDD sont 12 % moins chers
BASE_PRICES = {250: "1.65", 300: "2.15", 500: "2.95", 1000: "5.90"}
PRIVATE_LABEL_DISCOUNT = Decimal("0.88")


def _load_prices(today) -> int:
    count = 0
    valid_from = today - timedelta(days=365)
    for customer in Customer.objects.filter(active=True):
        for row in orders.orderable_articles(customer, today):
            article = row["article"]
            price = Decimal(BASE_PRICES.get(article.format_size, "2.50"))
            if article.brand_customer_id:
                price = (price * PRIVATE_LABEL_DISCOUNT).quantize(Decimal("0.01"))
            SalePrice.objects.update_or_create(
                customer=customer,
                article=article,
                valid_from=valid_from,
                defaults={"unit_price": price},
            )
            count += 1
    return count


@transaction.atomic
def load_demo_data() -> dict[str, int | str]:
    today = timezone.localdate()
    counts: dict[str, int | str] = {"tarifs de vente": _load_prices(today)}
    if CustomerOrder.objects.exists():
        counts["commandes clients"] = "déjà présentes, non modifiées"
        return counts

    # Commandes EDI reçues à 9 h 30 les 3 derniers jours (graine fixe : résultats reproductibles)
    messages = []
    for days_ago in (2, 1, 0):
        day = today - timedelta(days=days_ago)
        received_at = timezone.make_aware(datetime.combine(day, time(9, 30)))
        if received_at <= timezone.now():
            messages += edi.simulate_day(received_at, seed=1000 + days_ago)

    # Une commande saisie à la main (appel téléphonique de Proxi Ville après 11 h)
    proxi = Customer.objects.get(code="ENS4")
    received = timezone.make_aware(datetime.combine(today, time(14, 10)))
    if received <= timezone.now():
        orders.create_order(
            customer=proxi,
            warehouse=proxi.warehouses.order_by("code").first(),
            requested_delivery_date=orders.earliest_delivery_date(received),
            lines=[
                {"article": Article.objects.get(code="PF-PAT-LASBOL-BRE-300"), "quantity": 240},
                {"article": Article.objects.get(code="PF-ENT-CARAP-BRE-250"), "quantity": 120},
            ],
            customer_reference="Appel de M. Leroy (magasin de Vannes)",
            received_at=received,
            comment="Commande urgente par téléphone",
        )
    # Un message erroné, pour voir un rejet : Proxi Ville commande un produit MDD d'Hyper
    # Atlantique, avec une livraison le jour même
    sent_at = timezone.make_aware(datetime.combine(today, time(9, 55)))
    if sent_at <= timezone.now():
        messages.append(
            edi.integrate_message(
                {
                    "message_id": f"ENS4-{today:%Y%m%d}-ERR",
                    "sender": "ENS4",
                    "order_reference": "PV-ERREUR-DEMO",
                    "delivery_location": proxi.warehouses.order_by("code").first().code,
                    "requested_delivery_date": today.isoformat(),
                    "lines": [{"article": "PF-PAT-LASBOL-ENS1-300", "quantity": 120}],
                },
                received_at=sent_at,
            )
        )
    counts["messages EDI"] = len(messages)
    counts["rejetés"] = sum(1 for message in messages if message.status == "rejete")
    counts["commandes clients"] = CustomerOrder.objects.count()
    return counts
