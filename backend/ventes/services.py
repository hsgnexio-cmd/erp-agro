"""Déclaration d'expédition (version minimale de la phase 5).

La phase 7 ajoutera les commandes EDI, la préparation FEFO et les bons de livraison ;
elle s'appuiera sur cette fonction, qui garantit déjà la traçabilité aval (règle 1).
"""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from referentiel.choices import ArticleType
from referentiel.models import CustomerWarehouse, Location
from referentiel.services import next_document_number
from stocks import services as stock_services
from stocks.choices import LotStatus, MovementType
from stocks.models import Lot, StockMovement


def remaining_shelf_life_pct(lot: Lot, on_date: date) -> Decimal | None:
    """Part de la durée de vie totale qui reste au lot à une date (règle 5)."""
    if not lot.expiry_date or not lot.article.shelf_life_days:
        return None
    remaining_days = (lot.expiry_date - on_date).days
    return Decimal(remaining_days * 100) / Decimal(lot.article.shelf_life_days)


def check_lot_for_customer(lot: Lot, warehouse: CustomerWarehouse, on_date: date) -> None:
    """Contrôles propres au client : marque (MDD) et DLC minimale à la livraison."""
    customer = warehouse.customer
    article = lot.article
    if article.article_type == ArticleType.FINISHED_PRODUCT:
        # Règle 10 : un produit MDD ne part que chez son enseigne
        if article.brand_customer_id and article.brand_customer_id != customer.pk:
            raise ValidationError(
                f"{article.code} est un produit MDD de {article.brand_customer.code} : "
                f"il ne peut pas être livré à {customer.code}."
            )
        if not article.brand_customer_id and not customer.sells_brand:
            raise ValidationError(
                f"{customer.code} ne vend pas la marque Brévanne : {article.code} refusé."
            )
    # Règle 5 : DLC minimale exigée par l'enseigne
    remaining = remaining_shelf_life_pct(lot, on_date)
    minimum = customer.min_remaining_shelf_life_pct
    if remaining is not None and remaining < minimum:
        raise ValidationError(
            f"Lot {lot.number} trop court pour {customer.code} : il reste {remaining:.0f} % "
            f"de sa durée de vie, l'enseigne exige {minimum:.0f} %."
        )


@transaction.atomic
def record_shipment(
    *,
    lot: Lot,
    location: Location,
    quantity: Decimal,
    warehouse: CustomerWarehouse,
    user=None,
) -> StockMovement:
    """Déclare l'expédition d'une quantité d'un lot vers un entrepôt client."""
    today = timezone.localdate()
    # Relit et verrouille le lot : son statut et son stock sont ceux de cet instant
    lot = Lot.objects.select_for_update().get(pk=lot.pk)
    if lot.status != LotStatus.RELEASED:
        # Règle 6 : seul un lot libéré peut être expédié
        raise ValidationError(
            f"Le lot {lot.number} est {lot.get_status_display().lower()} : seul un lot libéré "
            "peut être expédié."
        )
    if stock_services.is_expired(lot, today):
        raise ValidationError(f"Le lot {lot.number} est périmé.")
    if not (warehouse.active and warehouse.customer.active):
        raise ValidationError({"warehouse": f"L'entrepôt {warehouse.code} est inactif."})
    if quantity <= 0:
        raise ValidationError({"quantity": "La quantité expédiée doit être positive."})
    available = stock_services.quantity_at(lot, location)
    if quantity > available:
        raise ValidationError(
            {
                "quantity": f"Stock insuffisant : {available.normalize():f} {lot.unit} du lot "
                f"{lot.number} en {location.code}."
            }
        )
    check_lot_for_customer(lot, warehouse, today)

    return StockMovement.objects.create(
        lot=lot,
        movement_type=MovementType.SHIPMENT,
        quantity=-quantity,
        location=location,
        user=user if user is not None and user.is_authenticated else None,
        reason=f"Expédition {warehouse.customer.code} – {warehouse.name}",
        reference=next_document_number(f"EXP-{today.year}", 5),
        customer_warehouse=warehouse,
    )
