"""Déclaration de fabrication (version minimale de la phase 5).

La phase 6 ajoutera les ordres de fabrication, la planification et les rendements ;
elle s'appuiera sur cette fonction, qui garantit déjà la traçabilité (règle 1).
"""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from referentiel.choices import ArticleType
from referentiel.models import Article, Location
from referentiel.services import next_document_number
from stocks import services as stock_services
from stocks.choices import LotStatus, MovementType
from stocks.models import Lot, StockMovement

ZERO = Decimal("0")


def next_produced_lot_number(production_date: date) -> str:
    """Numéro interne d'un lot fabriqué : LF-AAMMJJ-NNNN (LF = lot de fabrication)."""
    return next_document_number(f"LF-{production_date:%y%m%d}", 4)


def _user(user):
    return user if user is not None and user.is_authenticated else None


@transaction.atomic
def record_production(
    *,
    article: Article,
    quantity: Decimal,
    location: Location,
    consumptions: list[dict],
    production_date: date | None = None,
    user=None,
) -> Lot:
    """Déclare une fabrication : crée le lot fabriqué et consomme les lots utilisés.

    Chaque élément de `consumptions` contient : lot, location, quantity.
    """
    production_date = production_date or timezone.localdate()
    if article.article_type not in (ArticleType.SEMI_FINISHED, ArticleType.FINISHED_PRODUCT):
        raise ValidationError(
            {"article": "On ne fabrique que des semi-finis et des produits finis."}
        )
    if not hasattr(article, "bom"):
        raise ValidationError({"article": f"{article.code} n'a pas de nomenclature."})
    if quantity <= 0:
        raise ValidationError({"quantity": "La quantité fabriquée doit être positive."})
    if production_date > timezone.localdate():
        raise ValidationError(
            {"production_date": "La date de fabrication ne peut pas être future."}
        )
    if not consumptions:
        raise ValidationError({"consumptions": ["Indique au moins un lot consommé."]})
    stock_services.check_location_compatible(article, location)

    components = set(article.bom.lines.values_list("component_id", flat=True))
    errors = []
    for data in consumptions:
        # Relit et verrouille le lot : son statut et son stock sont ceux de cet instant
        lot = data["lot"] = Lot.objects.select_for_update().get(pk=data["lot"].pk)
        label = f"Lot {lot.number} ({lot.article.code})"
        if lot.article_id not in components:
            errors.append(
                f"{label} : cet article n'est pas dans la nomenclature de {article.code}."
            )
        elif lot.status != LotStatus.RELEASED:
            # Règle 6 : seul un lot libéré peut être consommé
            errors.append(f"{label} : lot {lot.get_status_display().lower()}, non consommable.")
        elif stock_services.is_expired(lot, production_date):
            errors.append(f"{label} : lot périmé ({lot.date_type} du {lot.expiry_date:%d/%m/%Y}).")
        elif data["quantity"] <= 0:
            errors.append(f"{label} : la quantité consommée doit être positive.")
        else:
            available = stock_services.quantity_at(lot, data["location"])
            if data["quantity"] > available:
                errors.append(
                    f"{label} : stock insuffisant en {data['location'].code} "
                    f"({available.normalize():f} {lot.unit})."
                )
    if errors:
        raise ValidationError({"consumptions": errors})

    number = next_produced_lot_number(production_date)
    produced = Lot.objects.create(
        number=number,
        article=article,
        production_date=production_date,
        date_type=article.date_type,
        # Règle 3 : DLC calculée à partir de la durée de vie de l'article
        expiry_date=stock_services.compute_expiry_date(article, production_date),
        initial_quantity=quantity,
        location=location,
        status=LotStatus.QUARANTINE,
    )
    StockMovement.objects.create(
        lot=produced,
        movement_type=MovementType.PRODUCTION,
        quantity=quantity,
        location=location,
        user=_user(user),
        reason="Fabrication",
        reference=number,
    )
    for data in consumptions:
        StockMovement.objects.create(
            lot=data["lot"],
            movement_type=MovementType.CONSUMPTION,
            quantity=-data["quantity"],
            location=data["location"],
            user=_user(user),
            reason=f"Consommé pour {article.code}",
            reference=number,
            produced_lot=produced,
        )
    return produced
