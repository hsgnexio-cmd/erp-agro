"""Règles métier des achats et des réceptions."""

from datetime import date, datetime, timedelta
from decimal import Decimal

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from referentiel.choices import TemperatureClass
from stocks.services import receive_lot

from .choices import PurchaseOrderStatus

# Contrôle à réception : température maximale selon la conservation (règle 7)
MAX_TEMPERATURE = {
    TemperatureClass.CHILLED: Decimal("4"),
    TemperatureClass.FROZEN: Decimal("-18"),
}
# Livraison acceptée jusqu'à la quantité commandée + 10 % (livraisons au poids)
OVER_DELIVERY_TOLERANCE = Decimal("0.10")

EDITABLE_STATUSES = (PurchaseOrderStatus.DRAFT,)
RECEIVABLE_STATUSES = (PurchaseOrderStatus.SENT, PurchaseOrderStatus.PARTIAL)


def _fr(value: Decimal) -> str:
    """Nombre au format français : 6.5 → « 6,5 »."""
    return f"{value.normalize():f}".replace(".", ",")


def _model(name: str):
    return apps.get_model("achats", name)


# --- Tarifs -----------------------------------------------------------------


def validate_supplier_price(price) -> None:
    if price.valid_to and price.valid_to < price.valid_from:
        raise ValidationError({"valid_to": "La date de fin précède la date de début."})
    if not price.supplier_article_id:
        return
    end = price.valid_to or date.max
    overlapping = (
        _model("SupplierPrice")
        .objects.filter(supplier_article=price.supplier_article, valid_from__lte=end)
        .exclude(valid_to__lt=price.valid_from)
        .exclude(pk=price.pk)
    )
    if overlapping.exists():
        raise ValidationError(
            "Un autre tarif existe déjà sur cette période : clôture-le d'abord (date de fin)."
        )


def current_price(supplier_article, on_date: date):
    """Tarif en vigueur à une date, ou None."""
    return (
        supplier_article.prices.filter(valid_from__lte=on_date)
        .exclude(valid_to__lt=on_date)
        .order_by("-valid_from")
        .first()
    )


# --- Commandes --------------------------------------------------------------


def validate_purchase_order(order) -> None:
    errors: dict[str, str] = {}
    if order.supplier_id and order.status == PurchaseOrderStatus.DRAFT:
        supplier = order.supplier
        if not supplier.active:
            errors["supplier"] = f"Le fournisseur {supplier.code} est inactif."
        elif not supplier.audited:
            errors["supplier"] = (
                f"Le fournisseur {supplier.code} n'est pas audité : "
                "commande impossible tant que son audit n'est pas enregistré."
            )
    if order.delivery_site_id and not order.delivery_site.active:
        errors["delivery_site"] = "Ce site est inactif."
    if order.supplier_id and order.order_date and not order.expected_delivery_date:
        order.expected_delivery_date = order.order_date + timedelta(
            days=order.supplier.lead_time_days
        )
    if (
        order.expected_delivery_date
        and order.order_date
        and order.expected_delivery_date < order.order_date
    ):
        errors["expected_delivery_date"] = "La livraison prévue précède la date de commande."
    if errors:
        raise ValidationError(errors)


def prepare_and_validate_order_line(line) -> None:
    if not (line.order_id and line.article_id):
        return
    order, article = line.order, line.article
    line.unit = article.unit

    if order.status not in EDITABLE_STATUSES:
        raise ValidationError(
            f"La commande {order.number} est {order.get_status_display().lower()} : "
            "elle n'est plus modifiable."
        )
    supplier_article = article.supplier_links.filter(supplier=order.supplier).first()
    if supplier_article is None:
        raise ValidationError({"article": f"article non référencé chez {order.supplier.name}."})
    minimum = supplier_article.min_order_quantity
    if minimum and line.quantity is not None and line.quantity < minimum:
        raise ValidationError(
            {
                "quantity": f"Quantité minimale de commande pour {article.code} : "
                f"{minimum.normalize():f} {article.unit}."
            }
        )
    if line.unit_price is None:
        price = current_price(supplier_article, order.order_date)
        if price is None:
            raise ValidationError(
                {"unit_price": f"Aucun tarif en vigueur pour {article.code} : indique le prix."}
            )
        line.unit_price = price.unit_price


def _save_lines(order, lines: list[dict]) -> None:
    if not lines:
        raise ValidationError({"lines": ["Une commande doit contenir au moins une ligne."]})
    errors = []
    for data in lines:
        try:
            _model("PurchaseOrderLine").objects.create(order=order, **data)
        except ValidationError as exc:
            errors.append(f"{data['article'].code} : {' '.join(exc.messages)}")
    if errors:
        raise ValidationError({"lines": errors})


@transaction.atomic
def create_purchase_order(*, lines: list[dict], user=None, **fields):
    """Crée une commande en brouillon avec ses lignes (article, quantity, unit_price)."""
    order = _model("PurchaseOrder")(created_by=user, **fields)
    order.save()
    _save_lines(order, lines)
    return order


@transaction.atomic
def update_purchase_order(order, *, lines: list[dict] | None = None, **fields):
    """Modifie une commande en brouillon ; `lines` remplace toutes les lignes."""
    if order.status not in EDITABLE_STATUSES:
        raise ValidationError("Seule une commande en brouillon peut être modifiée.")
    for name, value in fields.items():
        setattr(order, name, value)
    if "order_date" in fields or "supplier" in fields:
        if "expected_delivery_date" not in fields:
            order.expected_delivery_date = None
    order.save()
    if lines is not None:
        order.lines.all().delete()
        _save_lines(order, lines)
    return order


def send_order(order):
    if order.status != PurchaseOrderStatus.DRAFT:
        raise ValidationError("Seule une commande en brouillon peut être envoyée.")
    if not order.lines.exists():
        raise ValidationError("Impossible d'envoyer une commande sans ligne.")
    order.status = PurchaseOrderStatus.SENT
    order.sent_at = timezone.now()
    order.save()
    return order


def cancel_order(order):
    if order.status not in (PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.SENT):
        raise ValidationError(
            f"Une commande {order.get_status_display().lower()} ne peut pas être annulée."
        )
    if order.receptions.exists():
        raise ValidationError("Cette commande a déjà été réceptionnée : annulation impossible.")
    order.status = PurchaseOrderStatus.CANCELLED
    order.save()
    return order


def refresh_order_status(order) -> None:
    """Après une réception : commande soldée si tout est reçu, sinon partiellement reçue."""
    fully_received = all(line.received_quantity >= line.quantity for line in order.lines.all())
    order.status = PurchaseOrderStatus.CLOSED if fully_received else PurchaseOrderStatus.PARTIAL
    order.save()


# --- Réceptions -------------------------------------------------------------


def validate_reception(reception) -> None:
    if (
        reception.order_id
        and reception.location_id
        and reception.location.site_id != reception.order.delivery_site_id
    ):
        raise ValidationError(
            {
                "location": f"L'emplacement doit appartenir au site de livraison "
                f"({reception.order.delivery_site.code})."
            }
        )


def check_reception_controls(
    *,
    article,
    reception_date: date,
    expiry_date: date | None,
    temperature: Decimal | None,
    appearance_ok: bool,
    documents_ok: bool,
) -> list[str]:
    """Contrôles à réception. Renvoie la liste des non-conformités (vide = conforme)."""
    reasons = []

    # Règle 7 : chaîne du froid
    maximum = MAX_TEMPERATURE.get(article.storage_temperature_class)
    if maximum is not None and temperature is not None and temperature > maximum:
        reasons.append(
            f"Température de {_fr(temperature)} °C au-dessus du maximum de {_fr(maximum)} °C"
        )

    # DLC / DDM restante
    if expiry_date:
        if expiry_date <= reception_date:
            reasons.append(
                f"Produit périmé à réception ({article.date_type} du {expiry_date:%d/%m/%Y})"
            )
        elif article.category_id and article.shelf_life_days:
            remaining_days = (expiry_date - reception_date).days
            remaining_pct = Decimal(remaining_days * 100) / Decimal(article.shelf_life_days)
            minimum = article.category.min_remaining_shelf_life_pct
            if remaining_pct < minimum:
                reasons.append(
                    f"Durée de vie restante insuffisante : {remaining_pct:.0f} % "
                    f"(minimum {minimum:.0f} %)"
                )

    if not appearance_ok:
        reasons.append("Aspect non conforme")
    if not documents_ok:
        reasons.append("Documents de livraison manquants ou non conformes")
    return reasons


def _check_line_data(order, data: dict) -> list[str]:
    """Vérifie une ligne saisie avant de créer le lot. Renvoie les erreurs."""
    order_line = data["order_line"]
    article = order_line.article
    errors = []
    if order_line.order_id != order.id:
        return [f"{article.code} : cette ligne n'appartient pas à la commande {order.number}."]

    total = order_line.received_quantity + data["quantity"]
    maximum = order_line.quantity * (1 + OVER_DELIVERY_TOLERANCE)
    if total > maximum:
        errors.append(
            f"quantité reçue totale ({total.normalize():f}) supérieure à la commande "
            f"+ 10 % ({maximum.normalize():f} {article.unit})"
        )
    if not data.get("supplier_lot_number"):
        errors.append("le numéro de lot fournisseur est obligatoire")
    if article.date_type in ("DLC", "DDM") and not data.get("expiry_date"):
        errors.append(f"la {article.date_type} est obligatoire")
    if article.storage_temperature_class in MAX_TEMPERATURE and data.get("temperature") is None:
        errors.append("la température est obligatoire pour un produit frais ou surgelé")
    return [f"{article.code} : {message}" for message in errors]


@transaction.atomic
def create_reception(
    *,
    order,
    location,
    delivery_note_number: str,
    lines: list[dict],
    documents_ok: bool = True,
    received_at: datetime | None = None,
    comment: str = "",
    user=None,
):
    """Enregistre une réception : contrôles, création des lots et des mouvements d'entrée.

    Chaque ligne de `lines` contient : order_line, quantity, supplier_lot_number,
    expiry_date, temperature, appearance_ok (et un commentaire facultatif).
    """
    if order.status not in RECEIVABLE_STATUSES:
        raise ValidationError(
            f"La commande {order.number} est {order.get_status_display().lower()} : "
            "seule une commande envoyée peut être réceptionnée."
        )
    if not lines:
        raise ValidationError({"lines": ["Indique au moins une ligne reçue."]})

    reception = _model("Reception")(
        order=order,
        location=location,
        delivery_note_number=delivery_note_number,
        documents_ok=documents_ok,
        received_at=received_at or timezone.now(),
        received_by=user if user and user.is_authenticated else None,
        comment=comment,
    )
    reception.save()
    reception_date = timezone.localtime(reception.received_at).date()

    errors = []
    for data in lines:
        line_errors = _check_line_data(order, data)
        if line_errors:
            errors.extend(line_errors)
            continue
        article = data["order_line"].article
        reasons = check_reception_controls(
            article=article,
            reception_date=reception_date,
            expiry_date=data.get("expiry_date"),
            temperature=data.get("temperature"),
            appearance_ok=data.get("appearance_ok", True),
            documents_ok=documents_ok,
        )
        lot = receive_lot(
            article=article,
            supplier=order.supplier,
            quantity=data["quantity"],
            location=location,
            reception_date=reception_date,
            expiry_date=data.get("expiry_date"),
            supplier_lot_number=data["supplier_lot_number"],
            block_reasons=reasons,
            user=user,
            reference=reception.number,
        )
        _model("ReceptionLine").objects.create(
            reception=reception,
            order_line=data["order_line"],
            quantity=data["quantity"],
            supplier_lot_number=data["supplier_lot_number"],
            expiry_date=data.get("expiry_date"),
            temperature=data.get("temperature"),
            appearance_ok=data.get("appearance_ok", True),
            comment=data.get("comment", ""),
            is_compliant=not reasons,
            non_compliance_reasons=" ; ".join(reasons),
            lot=lot,
        )

    if errors:
        # Annule toute la réception (aucun lot ni mouvement n'est conservé)
        raise ValidationError({"lines": errors})

    refresh_order_status(order)
    return reception
