"""Tarifs de vente et commandes clients : règles de prise de commande."""

from datetime import date, datetime, time

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from referentiel import calendar
from referentiel.calendar import Activity
from referentiel.choices import ArticleType
from referentiel.models import Article, Customer, CustomerWarehouse
from referentiel.services import next_document_number

# Heure limite de commande (fiche entreprise) : avant 11 h → livrable dès J+1, après → J+2
ORDER_CUTOFF = time(11, 0)


def _model(name: str):
    return apps.get_model("ventes", name)


# --- Tarifs de vente ------------------------------------------------------------


def validate_sale_price(price) -> None:
    errors = {}
    if price.article_id:
        reason = orderable_refusal(price.customer, price.article) if price.customer_id else None
        if reason:
            errors["article"] = reason
    if price.valid_to and price.valid_to < price.valid_from:
        errors["valid_to"] = "La date de fin précède la date de début."
    if errors:
        raise ValidationError(errors)
    end = price.valid_to or date.max
    overlap = (
        _model("SalePrice")
        .objects.filter(customer=price.customer, article=price.article, valid_from__lte=end)
        .exclude(valid_to__lt=price.valid_from)
        .exclude(pk=price.pk)
    )
    if overlap.exists():
        raise ValidationError(
            "Un autre tarif existe déjà sur cette période : clôture-le d'abord (date de fin)."
        )


def current_sale_price(customer: Customer, article: Article, on_date: date):
    return (
        _model("SalePrice")
        .objects.filter(customer=customer, article=article, valid_from__lte=on_date)
        .exclude(valid_to__lt=on_date)
        .order_by("-valid_from")
        .first()
    )


# --- Règles de commande ------------------------------------------------------------


def orderable_refusal(customer: Customer, article: Article) -> str | None:
    """Raison pour laquelle l'enseigne ne peut pas commander l'article, ou None."""
    if article.article_type != ArticleType.FINISHED_PRODUCT:
        return f"{article.code} n'est pas un produit fini."
    if not article.active:
        return f"{article.code} n'est plus commercialisé."
    # Règle 10 : un produit MDD n'est vendu qu'à son enseigne
    if article.brand_customer_id and article.brand_customer_id != customer.pk:
        return f"{article.code} est un produit MDD de {article.brand_customer.code}."
    if not article.brand_customer_id and not customer.sells_brand:
        return f"{customer.code} ne vend pas la marque Brévanne."
    return None


def earliest_delivery_date(received_at: datetime) -> date:
    """Commande reçue avant 11 h un jour ouvré : livrable dès le jour de livraison suivant ;
    après 11 h : le jour de livraison d'après. Une commande reçue un dimanche ou un jour férié
    compte comme reçue le jour ouvré suivant au matin (phase 11)."""
    local = timezone.localtime(received_at)
    day, before_cutoff = local.date(), local.time() < ORDER_CUTOFF
    if not calendar.is_open(day, Activity.SHIPPING):
        day, before_cutoff = calendar.next_open_day(day, Activity.SHIPPING), True
    first = calendar.next_open_day(day, Activity.SHIPPING, strict=True)
    return first if before_cutoff else calendar.next_open_day(first, Activity.SHIPPING, strict=True)


def ship_by_date(delivery: date) -> date:
    """Transport en J+1 : expédié au plus tard le dernier jour d'expédition avant la livraison."""
    return calendar.previous_open_day(delivery, Activity.SHIPPING, strict=True)


def delivery_refusal(delivery: date) -> str | None:
    """Raison pour laquelle on ne livre pas ce jour-là (dimanche, férié…), ou None."""
    reason = calendar.closed_reason(delivery, Activity.SHIPPING)
    if not reason:
        return None
    possible = calendar.next_open_day(delivery, Activity.SHIPPING)
    return (
        f"Pas de livraison le {calendar.describe(delivery)} ({reason}) : "
        f"prochaine date possible le {calendar.describe(possible)}."
    )


@transaction.atomic
def create_order(
    *,
    customer: Customer,
    warehouse: CustomerWarehouse,
    requested_delivery_date: date,
    lines: list[dict],
    customer_reference: str = "",
    received_at: datetime | None = None,
    source: str = "manuel",
    comment: str = "",
    edi_message=None,
    user=None,
):
    """Crée une commande client. Chaque ligne : article, quantity."""
    received_at = received_at or timezone.now()
    errors: list[str] = []
    if not customer.active:
        errors.append(f"L'enseigne {customer.code} est inactive.")
    if warehouse.customer_id != customer.pk:
        errors.append(f"L'entrepôt {warehouse.code} n'appartient pas à {customer.code}.")
    elif not warehouse.active:
        errors.append(f"L'entrepôt {warehouse.code} est inactif.")
    earliest = earliest_delivery_date(received_at)
    refusal = delivery_refusal(requested_delivery_date)
    if refusal:
        errors.append(refusal)
    elif requested_delivery_date < earliest:
        errors.append(
            f"Livraison demandée le {requested_delivery_date:%d/%m/%Y} : trop tôt pour une "
            f"commande reçue le {timezone.localtime(received_at):%d/%m/%Y à %H:%M} "
            f"(au plus tôt le {calendar.describe(earliest)}, heure limite 11 h, jours ouvrés)."
        )
    if not lines:
        errors.append("La commande ne contient aucune ligne.")
    seen = set()
    for data in lines:
        article = data["article"]
        if article.pk in seen:
            errors.append(f"{article.code} : produit présent deux fois dans la commande.")
        seen.add(article.pk)
        reason = orderable_refusal(customer, article)
        if reason:
            errors.append(reason)
        if data["quantity"] is None or data["quantity"] < 1:
            errors.append(f"{article.code} : la quantité doit être d'au moins 1.")
    if errors:
        raise ValidationError(errors)

    order = _model("CustomerOrder").objects.create(
        number=next_document_number(f"CC-{timezone.localtime(received_at).year}", 5),
        customer=customer,
        warehouse=warehouse,
        customer_reference=customer_reference.strip(),
        received_at=received_at,
        requested_delivery_date=requested_delivery_date,
        ship_by_date=ship_by_date(requested_delivery_date),
        source=source,
        edi_message=edi_message,
        comment=comment.strip(),
        created_by=user if user is not None and user.is_authenticated else None,
    )
    for data in lines:
        price = current_sale_price(customer, data["article"], requested_delivery_date)
        _model("CustomerOrderLine").objects.create(
            order=order,
            article=data["article"],
            quantity=data["quantity"],
            # Sans tarif en vigueur, la ligne est acceptée mais reste « à valoriser »
            unit_price=price.unit_price if price else None,
        )
    return order


def cancel_order(order):
    if order.status != "recue":
        raise ValidationError(
            f"Une commande {order.get_status_display().lower()} ne peut plus être annulée."
        )
    order.status = "annulee"
    order.save(update_fields=["status"])
    return order


def orderable_articles(customer: Customer, on_date: date) -> list[dict]:
    """Produits que l'enseigne peut commander, avec le prix en vigueur."""
    articles = Article.objects.filter(article_type=ArticleType.FINISHED_PRODUCT, active=True)
    result = []
    for article in articles.select_related("brand_customer").order_by("code"):
        if orderable_refusal(customer, article) is None:
            price = current_sale_price(customer, article, on_date)
            result.append({"article": article, "unit_price": price.unit_price if price else None})
    return result
