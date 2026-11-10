"""Préparation FEFO, expédition, palettes SSCC et taux de service (partie 7b).

Parcours d'une commande client :
1. « Préparer » : le magasinier choisit les lots (proposés en FEFO, règle 4), sans mouvement
   de stock ; la commande passe « en préparation » et un bon de livraison BL-… est créé ;
2. « Expédier » : transporteur et température au chargement (règle 7), mouvements
   d'expédition (règle 11, traçabilité aval de la règle 1), palettes SSCC ; commande expédiée.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_CEILING, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from referentiel.models import Article, Customer, Site
from referentiel.services import next_document_number
from stocks import services as stock_services
from stocks.choices import AlertLevel, AlertType, LotStatus
from stocks.models import Lot
from stocks.monitoring import raise_alert

from .models import (
    CustomerOrder,
    OrderStatus,
    Pallet,
    PalletLine,
    Shipment,
    ShipmentLine,
    ShipmentStatus,
)
from .services import check_lot_for_customer, record_shipment

# Toutes les expéditions partent de la plateforme produits finis de Nantes
SHIPPING_SITE_CODE = "PFN"
# Chaîne du froid : au-dessus de 4 °C au chargement, l'expédition est refusée
MAX_LOADING_TEMPERATURE = Decimal("4")
# Une palette : 60 colis de 12 unités
PALLET_CAPACITY = Decimal("720")
# SSCC : extension + préfixe d'entreprise GS1 (fictif) + numéro de série + clé de contrôle
SSCC_EXTENSION = "0"
GS1_COMPANY_PREFIX = "3770000"
SSCC_SERIAL_DIGITS = 17 - len(SSCC_EXTENSION) - len(GS1_COMPANY_PREFIX)
# Objectif de taux de service de la fiche entreprise
SERVICE_RATE_TARGET = Decimal("98.5")

UNLIMITED = Decimal("1000000000")
ZERO = Decimal("0")


def _user(user):
    return user if user is not None and user.is_authenticated else None


def _fr(value: Decimal) -> str:
    return f"{value.normalize():f}".replace(".", ",")


def shipping_site() -> Site:
    site = Site.objects.filter(code=SHIPPING_SITE_CODE).first()
    if site is None:
        raise ValidationError(
            f"Plateforme d'expédition {SHIPPING_SITE_CODE} introuvable dans le référentiel."
        )
    return site


# --- DLC minimale client (règle 5) ---------------------------------------------------


def min_expiry_for(customer: Customer, article: Article, delivery_date: date) -> date | None:
    """DLC la plus courte acceptée par l'enseigne pour une livraison à cette date.

    Exemple : lasagnes 14 jours, enseigne à 70 % → au moins 9,8 jours restants à la
    livraison, donc DLC ≥ livraison + 10 jours.
    """
    if not article.shelf_life_days:
        return None
    days = Decimal(article.shelf_life_days) * customer.min_remaining_shelf_life_pct / 100
    return delivery_date + timedelta(days=int(days.to_integral_value(rounding=ROUND_CEILING)))


# --- Proposition FEFO (règle 4) ------------------------------------------------------


def _committed(exclude: Shipment | None = None) -> dict[tuple[int, int], Decimal]:
    """Quantités déjà mises de côté par les préparations en attente d'expédition."""
    lines = ShipmentLine.objects.filter(shipment__status=ShipmentStatus.PREPARED)
    if exclude is not None:
        lines = lines.exclude(shipment=exclude)
    rows = lines.values("lot", "location").annotate(total=Sum("quantity"))
    return {(row["lot"], row["location"]): row["total"] for row in rows}


@dataclass
class PickLine:
    lot: Lot
    location: object
    available: Decimal
    suggested: Decimal


def _fefo_lines(
    article: Article,
    site: Site,
    quantity: Decimal,
    min_expiry: date | None,
    committed: dict[tuple[int, int], Decimal],
) -> list[PickLine]:
    """Lots disponibles dans l'ordre FEFO (hors lots trop courts et quantités déjà préparées)."""
    plan = stock_services.fefo_plan(article, site, UNLIMITED, min_expiry_date=min_expiry)
    lines, remaining = [], quantity
    for line in plan.lines:
        available = line.available - committed.get((line.lot.pk, line.location.pk), ZERO)
        if available <= 0:
            continue
        suggested = min(available, max(remaining, ZERO))
        remaining -= suggested
        lines.append(PickLine(line.lot, line.location, available, suggested))
    return lines


def picking_proposal(order: CustomerOrder) -> list[dict]:
    """Pour chaque ligne de commande : lots proposés (pré-remplis), manquant, lots trop courts."""
    site = shipping_site()
    committed = _committed()
    result = []
    for line in order.lines.select_related("article"):
        min_expiry = min_expiry_for(order.customer, line.article, order.requested_delivery_date)
        lots = _fefo_lines(line.article, site, line.quantity, min_expiry, committed)
        covered = sum((item.suggested for item in lots), ZERO)
        too_short = []
        if min_expiry:
            for item in stock_services.fefo_plan(line.article, site, UNLIMITED).lines:
                if item.lot.expiry_date and item.lot.expiry_date < min_expiry:
                    too_short.append(item)
        result.append(
            {
                "order_line": line,
                "min_expiry_date": min_expiry,
                "lots": lots,
                "missing": max(line.quantity - covered, ZERO),
                "too_short": too_short,
            }
        )
    return result


# --- Préparation ---------------------------------------------------------------------


@transaction.atomic
def prepare_order(order: CustomerOrder, *, lines: list[dict], user=None) -> Shipment:
    """Enregistre les lots préparés pour une commande reçue (sans mouvement de stock).

    Chaque ligne : order_line, lot, location, quantity et, si le lot n'est pas celui proposé
    par le FEFO, justification. La quantité non préparée sera une rupture (pas de reliquat).
    """
    order = CustomerOrder.objects.select_for_update().get(pk=order.pk)
    if order.status != OrderStatus.RECEIVED:
        raise ValidationError(
            f"La commande {order.number} est {order.get_status_display().lower()} : seule une "
            "commande reçue se prépare."
        )
    site = shipping_site()
    lines = [data for data in lines if data.get("quantity") and data["quantity"] > 0]
    if not lines:
        raise ValidationError(
            "Aucune quantité préparée : il n'y a rien à expédier. Attends du stock ou fais "
            "annuler la commande par le commercial."
        )

    order_lines = {line.pk: line for line in order.lines.select_related("article")}
    errors: list[str] = []
    per_order_line: dict[int, Decimal] = defaultdict(lambda: ZERO)
    per_slot: dict[tuple[int, int], Decimal] = defaultdict(lambda: ZERO)
    for data in lines:
        order_line, lot, location = data["order_line"], data["lot"], data["location"]
        if order_line.pk not in order_lines:
            errors.append(
                f"La ligne {order_line.pk} n'appartient pas à la commande {order.number}."
            )
            continue
        if lot.article_id != order_line.article_id:
            errors.append(f"Le lot {lot.number} n'est pas du {order_line.article.code}.")
        if location.site_id != site.pk:
            errors.append(
                f"Lot {lot.number} : l'emplacement {location.code} n'est pas sur la plateforme "
                f"{site.code}."
            )
        per_order_line[order_line.pk] += data["quantity"]
        per_slot[(lot.pk, location.pk)] += data["quantity"]
    if errors:
        raise ValidationError({"lines": errors})

    # Pas de surplus : on ne livre jamais plus que la quantité commandée
    for pk, total in per_order_line.items():
        ordered = order_lines[pk].quantity
        if total > ordered:
            errors.append(
                f"{order_lines[pk].article.code} : {_fr(total)} préparés pour {_fr(ordered)} "
                "commandés."
            )

    # Lots relus et verrouillés : statut, date et stock de cet instant
    committed = _committed()
    lots = {
        lot.pk: lot
        for lot in Lot.objects.select_for_update()
        .select_related("article")
        .filter(pk__in={lot_pk for lot_pk, _ in per_slot})
    }
    for (lot_pk, location_pk), total in per_slot.items():
        lot = lots[lot_pk]
        location = next(d["location"] for d in lines if d["location"].pk == location_pk)
        available = stock_services.quantity_at(lot, location) - committed.get(
            (lot_pk, location_pk), ZERO
        )
        if total > available:
            errors.append(
                f"Lot {lot.number} en {location.code} : {_fr(max(available, ZERO))} {lot.unit} "
                f"disponibles (hors préparations en cours), {_fr(total)} demandés."
            )
    for lot in lots.values():
        if lot.status != LotStatus.RELEASED:
            errors.append(
                f"Le lot {lot.number} est {lot.get_status_display().lower()} : seul un lot "
                "libéré peut être préparé."
            )
        elif stock_services.is_expired(lot):
            errors.append(f"Le lot {lot.number} est périmé.")
        try:
            check_lot_for_customer(lot, order.warehouse, order.requested_delivery_date)
        except ValidationError as error:
            errors.extend(error.messages)

    # Règle 4 : les lots préparés doivent être ceux qui périment le premier
    for data in lines:
        order_line, lot = order_lines[data["order_line"].pk], lots[data["lot"].pk]
        min_expiry = min_expiry_for(
            order.customer, order_line.article, order.requested_delivery_date
        )
        expected = _fefo_lines(
            order_line.article, site, per_order_line[order_line.pk], min_expiry, committed
        )
        expected_lots = {item.lot.pk for item in expected if item.suggested > 0}
        data["fefo_justification"] = ""
        if lot.pk in expected_lots:
            continue
        justification = (data.get("justification") or "").strip()
        if justification:
            data["fefo_justification"] = justification[:200]
        else:
            proposed = sorted({item.lot.number for item in expected if item.suggested > 0})
            errors.append(
                f"Lot {lot.number} ({order_line.article.code}) hors FEFO : le système propose "
                f"{', '.join(proposed) or 'aucun lot'}. Justifie ce choix."
            )
    if errors:
        raise ValidationError({"lines": list(dict.fromkeys(errors))})

    shipment = Shipment.objects.create(
        number=next_document_number(f"BL-{timezone.localdate().year}", 5),
        order=order,
        prepared_by=_user(user),
    )
    for data in lines:
        ShipmentLine.objects.create(
            shipment=shipment,
            order_line=order_lines[data["order_line"].pk],
            lot=lots[data["lot"].pk],
            location=data["location"],
            quantity=data["quantity"],
            fefo_justification=data["fefo_justification"],
        )
    order.status = OrderStatus.PREPARING
    order.save(update_fields=["status"])
    return shipment


def _locked(shipment: Shipment) -> Shipment:
    return Shipment.objects.select_for_update().get(pk=shipment.pk)


@transaction.atomic
def cancel_preparation(shipment: Shipment, *, reason: str, user=None) -> Shipment:
    """Annule une préparation non expédiée : la commande redevient « reçue »."""
    shipment = _locked(shipment)
    if shipment.status != ShipmentStatus.PREPARED:
        raise ValidationError("Seule une préparation pas encore expédiée peut être annulée.")
    if not reason.strip():
        raise ValidationError({"reason": "Indique le motif de l'annulation."})
    shipment.status = ShipmentStatus.CANCELLED
    shipment.refusal_reason = reason.strip()
    shipment.shipped_at = timezone.now()
    shipment.shipped_by = _user(user)
    shipment.save()
    order = CustomerOrder.objects.select_for_update().get(pk=shipment.order_id)
    order.status = OrderStatus.RECEIVED
    order.save(update_fields=["status"])
    return shipment


# --- Expédition ----------------------------------------------------------------------


@transaction.atomic
def ship_order(
    shipment: Shipment, *, carrier: str, temperature: Decimal | None, user=None
) -> Shipment:
    """Expédie une commande préparée, après contrôle de la température au chargement.

    Au-dessus de 4 °C (règle 7) : expédition refusée, lots préparés bloqués, alerte
    critique ; la commande redevient « reçue » (à préparer de nouveau, avec d'autres lots).
    """
    shipment = _locked(shipment)
    if shipment.status != ShipmentStatus.PREPARED:
        raise ValidationError(
            f"Le bon de livraison {shipment.number} est "
            f"{shipment.get_status_display().lower()} : il ne peut plus être expédié."
        )
    errors = {}
    if not (carrier or "").strip():
        errors["carrier"] = "Indique le transporteur."
    if temperature is None:
        errors["temperature"] = "La température au chargement est obligatoire."
    if errors:
        raise ValidationError(errors)

    order = CustomerOrder.objects.select_for_update().get(pk=shipment.order_id)
    lines = list(shipment.lines.select_related("lot__article", "location", "order_line"))
    shipment.carrier = carrier.strip()
    shipment.loading_temperature = temperature
    shipment.shipped_at = timezone.now()
    shipment.shipped_by = _user(user)

    if temperature > MAX_LOADING_TEMPERATURE:
        reason = (
            f"Température de {_fr(temperature)} °C au chargement du {shipment.number} "
            f"(maximum {_fr(MAX_LOADING_TEMPERATURE)} °C)"
        )
        blocked = []
        for lot in {line.lot.pk: line.lot for line in lines}.values():
            lot.refresh_from_db()
            if lot.status in (LotStatus.RELEASED, LotStatus.QUARANTINE):
                stock_services.block_lot(lot, user=user, reason=reason)
                blocked.append(lot.number)
        shipment.status = ShipmentStatus.REFUSED
        shipment.refusal_reason = reason
        shipment.save()
        order.status = OrderStatus.RECEIVED
        order.save(update_fields=["status"])
        raise_alert(
            AlertType.SHIPPING_TEMPERATURE,
            AlertLevel.CRITICAL,
            f"Expédition refusée : {reason}. Commande {order.number} ({order.customer.code}). "
            f"Lots bloqués : {', '.join(blocked) or 'aucun'}.",
            location=lines[0].location if lines else None,
            allow_duplicate=True,
        )
        return shipment

    for line in lines:
        try:
            line.movement = record_shipment(
                lot=line.lot,
                location=line.location,
                quantity=line.quantity,
                warehouse=order.warehouse,
                user=user,
                delivery_date=order.requested_delivery_date,
                reference=shipment.number,
            )
        except ValidationError as error:
            raise ValidationError(
                [
                    *error.messages,
                    "Annule la préparation, puis prépare de nouveau la commande.",
                ]
            ) from error
        line.save(update_fields=["movement"])
    build_pallets(shipment)
    shipment.status = ShipmentStatus.SHIPPED
    shipment.save()
    order.status = OrderStatus.SHIPPED
    order.save(update_fields=["status"])
    return shipment


# --- Palettes et SSCC ----------------------------------------------------------------


def gs1_check_digit(digits: str) -> int:
    """Clé de contrôle GS1 (modulo 10) : pondérations 3 et 1 en partant de la droite."""
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(digits)))
    return (10 - total % 10) % 10


def sscc_from_serial(serial: int) -> str:
    if not 0 < serial < 10**SSCC_SERIAL_DIGITS:
        raise ValidationError("Numéro de série SSCC hors limites.")
    body = f"{SSCC_EXTENSION}{GS1_COMPANY_PREFIX}{serial:0{SSCC_SERIAL_DIGITS}d}"
    return f"{body}{gs1_check_digit(body)}"


def next_sscc() -> str:
    """SSCC suivant (compteur en base, sans doublon)."""
    number = next_document_number("SSCC", SSCC_SERIAL_DIGITS)
    return sscc_from_serial(int(number.rsplit("-", 1)[1]))


def build_pallets(shipment: Shipment) -> list[Pallet]:
    """Répartit les lignes préparées sur des palettes de 720 unités au maximum."""
    pallets: list[Pallet] = []
    space = ZERO
    for line in shipment.lines.order_by("id"):
        remaining = line.quantity
        while remaining > 0:
            if not pallets or space <= 0:
                pallets.append(
                    Pallet.objects.create(
                        shipment=shipment, sscc=next_sscc(), rank=len(pallets) + 1
                    )
                )
                space = PALLET_CAPACITY
            take = min(remaining, space)
            PalletLine.objects.create(pallet=pallets[-1], shipment_line=line, quantity=take)
            remaining -= take
            space -= take
    return pallets


# --- Taux de service -----------------------------------------------------------------


def on_time_limit(order: CustomerOrder) -> date:
    """Transport en J+1 : expédié au plus tard le dernier jour d'expédition avant la livraison
    (le samedi pour une livraison le lundi), date calculée à la prise de commande."""
    if order.ship_by_date is not None:
        return order.ship_by_date
    from .orders import ship_by_date

    return ship_by_date(order.requested_delivery_date)


def _empty_row() -> dict:
    return {
        "ordered": ZERO,
        "on_time": ZERO,
        "late": ZERO,
        "missing": ZERO,
        "orders": 0,
        "perfect_orders": 0,
        "pending_orders": 0,
    }


def _finish(row: dict) -> dict:
    rate = None
    if row["ordered"]:
        rate = (row["on_time"] / row["ordered"] * 100).quantize(Decimal("0.1"))
    row["rate"] = rate
    row["below_target"] = rate is not None and rate < SERVICE_RATE_TARGET
    return row


def service_rate(
    *, start: date, end: date, customer: Customer | None = None, today: date | None = None
) -> dict:
    """Taux de service = quantité livrée complète et à l'heure ÷ quantité commandée.

    Commandes dont la livraison demandée tombe dans la période, hors commandes annulées.
    Une commande pas encore expédiée mais encore dans les temps est « en cours » et n'est
    pas comptée ; au-delà, elle compte comme non livrée.
    """
    today = today or timezone.localdate()
    orders = (
        CustomerOrder.objects.filter(requested_delivery_date__range=(start, end))
        .exclude(status=OrderStatus.CANCELLED)
        .select_related("customer")
        .prefetch_related("lines__article", "shipments__lines")
        .order_by("requested_delivery_date", "number")
    )
    if customer is not None:
        orders = orders.filter(customer=customer)

    rows: dict[int, dict] = {}
    customers: dict[int, Customer] = {}
    issues = []
    for order in orders:
        row = rows.setdefault(order.customer_id, _empty_row())
        customers[order.customer_id] = order.customer
        shipped = next(
            (s for s in order.shipments.all() if s.status == ShipmentStatus.SHIPPED), None
        )
        limit = on_time_limit(order)
        if shipped is None and today <= limit:
            row["pending_orders"] += 1
            continue
        on_time = shipped is not None and timezone.localdate(shipped.shipped_at) <= limit
        delivered_by_line: dict[int, Decimal] = defaultdict(lambda: ZERO)
        if shipped is not None:
            for line in shipped.lines.all():
                delivered_by_line[line.order_line_id] += line.quantity
        ordered = delivered = ZERO
        for line in order.lines.all():
            done = min(delivered_by_line[line.pk], line.quantity)
            ordered += line.quantity
            delivered += done
        row["orders"] += 1
        row["ordered"] += ordered
        row["missing"] += ordered - delivered
        if on_time:
            row["on_time"] += delivered
        else:
            row["late"] += delivered
        complete = delivered == ordered
        if on_time and complete:
            row["perfect_orders"] += 1
            continue
        if shipped is None:
            problem = "non expédiée"
        elif not on_time and not complete:
            problem = "en retard et incomplète"
        elif not on_time:
            problem = "en retard"
        else:
            problem = "incomplète (rupture)"
        issues.append(
            {
                "order": order,
                "problem": problem,
                "ordered": ordered,
                "delivered": delivered,
                "shipped_at": shipped.shipped_at if shipped else None,
            }
        )

    total = _empty_row()
    for row in rows.values():
        for key in total:
            total[key] += row[key]
    return {
        "start": start,
        "end": end,
        "target": SERVICE_RATE_TARGET,
        "customers": [
            {"customer": customers[pk], **_finish(row)}
            for pk, row in sorted(rows.items(), key=lambda item: customers[item[0]].code)
        ],
        "total": _finish(total),
        "issues": issues,
    }
