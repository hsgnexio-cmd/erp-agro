"""EDI simulé : réception et intégration des messages de commande des enseignes.

Format d'un message (JSON), inspiré d'un message EDIFACT ORDERS simplifié :
{
  "message_id": "ENS1-20261104-001",
  "sender": "ENS1",
  "order_reference": "HA-458812",
  "delivery_location": "ENS1-E01",
  "requested_delivery_date": "2026-11-05",
  "lines": [{"article": "PF-PAT-LASBOL-BRE-300", "quantity": 480}]
}
"""

import random
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from referentiel.models import Article, Customer, CustomerWarehouse

from . import orders
from .models import EdiMessage, EdiStatus

REQUIRED_FIELDS = ("message_id", "sender", "delivery_location", "requested_delivery_date", "lines")


def _reject(message: EdiMessage, errors: list[str]) -> EdiMessage:
    message.status = EdiStatus.REJECTED
    message.errors = errors
    message.save(update_fields=["status", "errors"])
    return message


def integrate_message(payload: dict, *, received_at: datetime | None = None) -> EdiMessage:
    """Enregistre le message, puis crée la commande ou rejette le message avec les motifs."""
    received_at = received_at or timezone.now()
    message_id = str(payload.get("message_id", "")).strip() if isinstance(payload, dict) else ""
    customer = None
    if isinstance(payload, dict):
        customer = Customer.objects.filter(code=str(payload.get("sender", "")).upper()).first()
    message = EdiMessage.objects.create(
        message_id=message_id or "(sans identifiant)",
        customer=customer,
        received_at=received_at,
        payload=payload,
    )

    if not isinstance(payload, dict):
        return _reject(message, ["Le message n'est pas un objet JSON."])
    missing = [name for name in REQUIRED_FIELDS if not payload.get(name)]
    if missing:
        return _reject(message, [f"Champ(s) manquant(s) : {', '.join(missing)}."])
    if (
        EdiMessage.objects.filter(message_id=message_id, status=EdiStatus.INTEGRATED)
        .exclude(pk=message.pk)
        .exists()
    ):
        return _reject(message, [f"Message {message_id} déjà intégré : doublon ignoré."])

    errors = []
    if customer is None:
        errors.append(f"Enseigne émettrice inconnue : {payload['sender']}.")
    warehouse = CustomerWarehouse.objects.filter(
        code=str(payload["delivery_location"]).upper()
    ).first()
    if warehouse is None:
        errors.append(f"Entrepôt de livraison inconnu : {payload['delivery_location']}.")
    delivery_date = parse_date(str(payload["requested_delivery_date"]))
    if delivery_date is None:
        errors.append(f"Date de livraison illisible : {payload['requested_delivery_date']}.")
    lines = []
    for raw in payload["lines"] if isinstance(payload["lines"], list) else []:
        code = str(raw.get("article", "")).upper()
        article = Article.objects.filter(code=code).first()
        if article is None:
            errors.append(f"Article inconnu : {code or '(vide)'}.")
            continue
        try:
            quantity = Decimal(str(raw.get("quantity")))
        except InvalidOperation:
            errors.append(f"{code} : quantité illisible.")
            continue
        lines.append({"article": article, "quantity": quantity})
    if not isinstance(payload["lines"], list):
        errors.append("Les lignes de commande sont illisibles.")
    if errors:
        return _reject(message, errors)

    try:
        with transaction.atomic():
            orders.create_order(
                customer=customer,
                warehouse=warehouse,
                requested_delivery_date=delivery_date,
                lines=lines,
                customer_reference=str(payload.get("order_reference", "")),
                received_at=received_at,
                source="edi",
                edi_message=message,
            )
    except ValidationError as exc:
        return _reject(message, exc.messages)

    message.status = EdiStatus.INTEGRATED
    message.save(update_fields=["status"])
    return message


# --- Simulation --------------------------------------------------------------------

# Environ un message sur dix contient une erreur volontaire, pour montrer le rejet
ERROR_RATE = 0.1


def _next_message_id(customer: Customer, day) -> str:
    prefix = f"{customer.code}-{day:%Y%m%d}-"
    count = EdiMessage.objects.filter(message_id__startswith=prefix).count()
    return f"{prefix}{count + 1:03d}"


def build_payload(customer: Customer, received_at: datetime, rng: random.Random) -> dict | None:
    """Commande réaliste d'une enseigne : son assortiment habituel, quantités par colis de 12."""
    delivery = orders.earliest_delivery_date(received_at)
    assortment = [
        row["article"]
        for row in orders.orderable_articles(customer, delivery)
        if row["unit_price"] is not None
    ]
    warehouses = list(customer.warehouses.filter(active=True).order_by("code"))
    if not assortment or not warehouses:
        return None
    chosen = rng.sample(assortment, k=min(len(assortment), rng.randint(2, 5)))
    day = timezone.localtime(received_at).date()
    payload = {
        "message_id": _next_message_id(customer, day),
        "sender": customer.code,
        "order_reference": f"{customer.code}-PO-{rng.randint(100000, 999999)}",
        "delivery_location": rng.choice(warehouses).code,
        "requested_delivery_date": delivery.isoformat(),
        "lines": [
            {"article": article.code, "quantity": 12 * rng.randint(10, 60)} for article in chosen
        ],
    }
    if rng.random() < ERROR_RATE:
        _inject_error(payload, customer, received_at, rng)
    return payload


def _inject_error(payload: dict, customer: Customer, received_at: datetime, rng) -> None:
    kind = rng.choice(["article_inconnu", "mdd_autre_enseigne", "livraison_trop_tot"])
    if kind == "article_inconnu":
        payload["lines"].append({"article": "PF-PAT-INCONNU-BRE-300", "quantity": 120})
    elif kind == "mdd_autre_enseigne":
        other = (
            Article.objects.filter(brand_customer__isnull=False, active=True)
            .exclude(brand_customer=customer)
            .order_by("code")
            .first()
        )
        if other is not None:
            payload["lines"].append({"article": other.code, "quantity": 120})
    else:
        payload["requested_delivery_date"] = timezone.localtime(received_at).date().isoformat()


def simulate_day(received_at: datetime | None = None, seed: int | None = None) -> list[EdiMessage]:
    """Une commande EDI par enseigne active, reçue à l'heure indiquée (9 h 30 par défaut)."""
    rng = random.Random(seed)
    received_at = received_at or timezone.now()
    messages = []
    for customer in Customer.objects.filter(active=True).order_by("code"):
        payload = build_payload(customer, received_at, rng)
        if payload is not None:
            messages.append(integrate_message(payload, received_at=received_at))
            received_at += timedelta(minutes=rng.randint(1, 7))
    return messages
