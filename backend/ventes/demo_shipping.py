"""Données de démonstration de la préparation et de l'expédition (partie 7b).

Le stock de produits finis de la plateforme est petit (lots de la phase 5) : on crée donc
quatre commandes à la mesure de ce stock, pour montrer chaque cas :
- Hyper Atlantique (ENS1) : complète et à l'heure ;
- Marché Plus (ENS2) : rupture sur le bœuf bourguignon (pas de reliquat) ;
- Coopérative Ouest (ENS3) : expédiée le jour de la livraison demandée, donc en retard ;
- Proxi Ville (ENS4) : refusée au chargement (5,8 °C), lot de gratin bloqué, puis détruit
  comme invendable.
Les lots de lasagnes concernés par le rappel de démonstration (crème CB-0412) gardent du stock.
"""

from datetime import datetime, time
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from referentiel import calendar
from referentiel.calendar import Activity
from referentiel.models import Article, Customer
from stocks import services as stock_services
from stocks.choices import UnsoldDestination
from stocks.models import Lot

from . import orders, shipping
from .models import CustomerOrder, Shipment

REFERENCE = "DEMO-7B"


def _order(customer_code: str, lines: list[tuple[str, int]], received_at, delivery):
    customer = Customer.objects.get(code=customer_code)
    return orders.create_order(
        customer=customer,
        warehouse=customer.warehouses.order_by("code").first(),
        requested_delivery_date=delivery,
        lines=[
            {"article": Article.objects.get(code=code), "quantity": Decimal(quantity)}
            for code, quantity in lines
        ],
        customer_reference=f"{REFERENCE}-{customer_code}",
        received_at=received_at,
        comment="Commande de démonstration de la préparation et de l'expédition",
    )


def _prepare_fefo(order: CustomerOrder) -> Shipment:
    """Prépare la commande avec les lots proposés par le FEFO, comme l'écran par défaut."""
    lines = [
        {
            "order_line": row["order_line"],
            "lot": item.lot,
            "location": item.location,
            "quantity": item.suggested,
        }
        for row in shipping.picking_proposal(order)
        for item in row["lots"]
        if item.suggested > 0
    ]
    return shipping.prepare_order(order, lines=lines)


@transaction.atomic
def load_demo_data() -> dict[str, int | str]:
    if Shipment.objects.exists():
        return {"expéditions": "déjà présentes, non modifiées"}
    needed = ("PF-PAT-LASBOL-ENS1-300", "PF-PAT-LASBOL-BRE-300", "PF-GRA-GRADAU-BRE-1000")
    if Lot.objects.filter(article__code__in=needed, status="libere").count() < len(needed):
        return {"expéditions": "pas de stock de produits finis à la plateforme, rien à faire"}

    today = timezone.localdate()
    # Commandes reçues le dernier jour ouvré avant aujourd'hui, avant l'heure limite (phase 11 :
    # dates calées sur le calendrier, jamais une livraison un dimanche ou un jour férié)
    order_day = calendar.previous_open_day(today, Activity.SHIPPING, strict=True)

    def received(minute: int):
        return timezone.make_aware(datetime.combine(order_day, time(9, minute)))

    due = orders.earliest_delivery_date(received(0))  # à expédier la veille : déjà en retard
    tomorrow = calendar.next_open_day(due, Activity.SHIPPING, strict=True)
    complete = _order("ENS1", [("PF-PAT-LASBOL-ENS1-300", 120)], received(5), tomorrow)
    partial = _order(
        "ENS2",
        [
            ("PF-PAT-LASBOL-BRE-300", 96),
            ("PF-GRA-GRADAU-BRE-1000", 120),
            ("PF-SAU-BOEBOU-BRE-300", 120),  # aucun stock : rupture
        ],
        received(12),
        tomorrow,
    )
    late = _order("ENS3", [("PF-GRA-GRADAU-BRE-1000", 24)], received(20), due)
    refused = _order("ENS4", [("PF-GRA-GRADAU-BRE-1000", 12)], received(31), tomorrow)

    for order, carrier in (
        (complete, "Transports Frigo Atlantique"),
        (partial, "Transports Frigo Atlantique"),
        (late, "Translog Froid Ouest"),
    ):
        shipping.ship_order(_prepare_fefo(order), carrier=carrier, temperature=Decimal("2.8"))

    # Camion mal pré-refroidi : expédition refusée, le lot de gratin est bloqué
    shipment = shipping.ship_order(
        _prepare_fefo(refused), carrier="Translog Froid Ouest", temperature=Decimal("5.8")
    )
    gratin = shipment.lines.get().lot
    gratin.refresh_from_db()
    stock_services.dispose_unsold(
        gratin,
        destination=UnsoldDestination.DESTRUCTION,
        reason="Rupture de la chaîne du froid au chargement : impropre au don",
    )
    return {
        "bons de livraison": Shipment.objects.count(),
        "palettes": sum(s.pallets.count() for s in Shipment.objects.all()),
        "invendables sortis": 1,
    }
