"""Logique métier des stocks : lots, statuts, mouvements, FEFO (règles 2, 3, 4, 6 et 11)."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from referentiel.choices import ArticleType, TemperatureClass
from referentiel.models import Article, Location, Site, Supplier
from referentiel.services import next_document_number

from .choices import LotStatus, MovementType, UnsoldDestination
from .models import Lot, LotStatusChange, StockMovement

ZERO = Decimal("0")


# --- Dates ------------------------------------------------------------------


def compute_expiry_date(article: Article, production_date: date) -> date:
    """Règle 3 : DLC (ou DDM) d'un produit fabriqué = date de fabrication + durée de vie."""
    if not article.shelf_life_days:
        raise ValidationError(f"L'article {article.code} n'a pas de durée de vie.")
    return production_date + timedelta(days=article.shelf_life_days)


def is_expired(lot: Lot, on_date: date | None = None) -> bool:
    """Un lot est périmé le lendemain de sa DLC/DDM."""
    on_date = on_date or timezone.localdate()
    return lot.expiry_date is not None and lot.expiry_date < on_date


# --- Emplacements et quantités ----------------------------------------------


def check_location_compatible(article: Article, location: Location) -> None:
    """Chaîne du froid : un lot ne va que dans un emplacement à la bonne température.

    Frais → froid positif, surgelé → froid négatif, sec et emballages → ambiant.
    """
    expected = article.storage_temperature_class
    if location.temperature_class != expected:
        needed = TemperatureClass(expected).label
        actual = location.get_temperature_class_display()
        raise ValidationError(
            {
                "location": f"{article.code} se conserve en « {needed} » : "
                f"l'emplacement {location.code} est en « {actual} »."
            }
        )


def quantity_at(lot: Lot, location: Location) -> Decimal:
    total = lot.movements.filter(location=location).aggregate(total=Sum("quantity"))["total"]
    return total or ZERO


def stock_by_location(lot: Lot) -> list[tuple[Location, Decimal]]:
    """Stock actuel d'un lot, emplacement par emplacement (seulement les quantités non nulles)."""
    rows = (
        lot.movements.values("location")
        .annotate(total=Sum("quantity"))
        .exclude(total=0)
        .order_by("location__code")
    )
    locations = Location.objects.in_bulk([row["location"] for row in rows])
    return [(locations[row["location"]], row["total"]) for row in rows]


def _lock(lot: Lot) -> Lot:
    """Verrouille le lot pendant l'opération : deux personnes ne le modifient pas en même temps."""
    return Lot.objects.select_for_update().get(pk=lot.pk)


# --- Réception ----------------------------------------------------------------


def next_received_lot_number(reception_date: date) -> str:
    """Numéro interne d'un lot reçu : LR-AAMMJJ-NNNN (LR = lot de réception)."""
    return next_document_number(f"LR-{reception_date:%y%m%d}", 4)


@transaction.atomic
def receive_lot(
    *,
    article: Article,
    supplier: Supplier,
    quantity: Decimal,
    location: Location,
    reception_date: date,
    expiry_date: date | None,
    supplier_lot_number: str,
    block_reasons: list[str],
    user,
    reference: str,
) -> Lot:
    """Crée un lot reçu et son mouvement d'entrée.

    Règle 6 : un lot reçu démarre en quarantaine, ou bloqué si un contrôle a échoué.
    """
    check_location_compatible(article, location)
    lot = Lot.objects.create(
        number=next_received_lot_number(reception_date),
        article=article,
        supplier=supplier,
        supplier_lot_number=supplier_lot_number,
        reception_date=reception_date,
        date_type=article.date_type,
        expiry_date=expiry_date,
        initial_quantity=quantity,
        location=location,
        status=LotStatus.BLOCKED if block_reasons else LotStatus.QUARANTINE,
        block_reason=" ; ".join(block_reasons),
    )
    StockMovement.objects.create(
        lot=lot,
        movement_type=MovementType.RECEPTION,
        quantity=quantity,
        location=location,
        user=_user_or_none(user),
        reason="Réception fournisseur",
        reference=reference,
    )
    return lot


def _user_or_none(user):
    return user if user is not None and user.is_authenticated else None


# --- Statuts (règle 6) ------------------------------------------------------

# Passages autorisés entre statuts
TRANSITIONS: dict[str, set[str]] = {
    LotStatus.QUARANTINE: {LotStatus.RELEASED, LotStatus.BLOCKED},
    LotStatus.RELEASED: {LotStatus.BLOCKED},
    LotStatus.BLOCKED: {LotStatus.RELEASED, LotStatus.DESTROYED},
    LotStatus.DESTROYED: set(),
}


@transaction.atomic
def change_status(
    lot: Lot,
    new_status: str,
    *,
    user=None,
    reason: str = "",
    exit_movement_type: str = MovementType.DESTRUCTION,
) -> Lot:
    """Change le statut d'un lot en respectant les règles, et l'inscrit au journal.

    À la destruction, le stock restant sort par des mouvements de type `exit_movement_type`
    (destruction, ou don / alimentation animale pour un invendable).
    """
    lot = _lock(lot)
    old_status = lot.status
    reason = reason.strip()

    if new_status not in TRANSITIONS[old_status]:
        raise ValidationError(
            f"Passage impossible de « {LotStatus(old_status).label} » "
            f"à « {LotStatus(new_status).label} » pour le lot {lot.number}."
        )
    needs_reason = new_status in (LotStatus.BLOCKED, LotStatus.DESTROYED) or (
        old_status == LotStatus.BLOCKED
    )
    if needs_reason and not reason:
        raise ValidationError({"reason": "Indique le motif de ce changement de statut."})
    if new_status == LotStatus.RELEASED and is_expired(lot):
        raise ValidationError(
            f"Le lot {lot.number} est périmé ({lot.date_type} du {lot.expiry_date:%d/%m/%Y}) : "
            "il ne peut pas être libéré."
        )

    if new_status == LotStatus.DESTROYED:
        # Toute la quantité restante sort du stock
        for location, quantity in stock_by_location(lot):
            StockMovement.objects.create(
                lot=lot,
                movement_type=exit_movement_type,
                quantity=-quantity,
                location=location,
                user=_user_or_none(user),
                reason=reason,
            )

    lot.status = new_status
    if new_status == LotStatus.BLOCKED:
        lot.block_reason = reason
    elif new_status == LotStatus.RELEASED:
        lot.block_reason = ""
    lot.save()
    LotStatusChange.objects.create(
        lot=lot,
        from_status=old_status,
        to_status=new_status,
        reason=reason,
        user=_user_or_none(user),
    )
    return lot


def release_lot(lot: Lot, *, user=None, reason: str = "") -> Lot:
    return change_status(lot, LotStatus.RELEASED, user=user, reason=reason)


def block_lot(lot: Lot, *, user=None, reason: str) -> Lot:
    return change_status(lot, LotStatus.BLOCKED, user=user, reason=reason)


def destroy_lot(lot: Lot, *, user=None, reason: str) -> Lot:
    return change_status(lot, LotStatus.DESTROYED, user=user, reason=reason)


# --- Invendables -------------------------------------------------------------

UNSOLD_MOVEMENT_TYPES = {
    UnsoldDestination.DONATION: MovementType.DONATION,
    UnsoldDestination.ANIMAL_FEED: MovementType.ANIMAL_FEED,
    UnsoldDestination.DESTRUCTION: MovementType.UNSOLD_DESTRUCTION,
}


@transaction.atomic
def dispose_unsold(lot: Lot, *, destination: str, reason: str, user=None) -> Lot:
    """Sort un produit fini invendable (bloqué ou périmé) vers sa destination.

    Tout le stock restant sort par un mouvement propre à la destination (don, alimentation
    animale, destruction) et le lot passe au statut « détruit », définitif.
    """
    lot = _lock(lot)
    reason = reason.strip()
    if destination not in UNSOLD_MOVEMENT_TYPES:
        raise ValidationError(
            {"destination": "Choisis la destination : don, alimentation animale ou destruction."}
        )
    if not reason:
        raise ValidationError({"reason": "Indique le motif de la sortie en invendable."})
    if len(reason) > 150:
        raise ValidationError({"reason": "Motif trop long (150 caractères au maximum)."})
    if lot.article.article_type != ArticleType.FINISHED_PRODUCT:
        raise ValidationError(
            f"Le lot {lot.number} n'est pas un produit fini : seuls les produits finis sortent "
            "en invendable (une matière se détruit depuis sa fiche lot)."
        )
    if lot.status == LotStatus.DESTROYED:
        raise ValidationError(f"Le lot {lot.number} est déjà sorti du stock (détruit).")
    expired = is_expired(lot)
    if lot.status != LotStatus.BLOCKED and not expired:
        raise ValidationError(
            f"Le lot {lot.number} est {lot.get_status_display().lower()} et encore dans sa date : "
            "seul un lot bloqué ou périmé sort en invendable."
        )
    if not stock_by_location(lot):
        raise ValidationError(f"Le lot {lot.number} n'a plus de stock.")

    label = UnsoldDestination(destination).label
    full_reason = f"Invendable – {label} : {reason}"
    if lot.status != LotStatus.BLOCKED:
        # Un lot périmé encore libéré ou en quarantaine est d'abord bloqué (journal des statuts)
        lot = change_status(lot, LotStatus.BLOCKED, user=user, reason=f"Périmé – {full_reason}")
    return change_status(
        lot,
        LotStatus.DESTROYED,
        user=user,
        reason=full_reason,
        exit_movement_type=UNSOLD_MOVEMENT_TYPES[destination],
    )


# --- Mouvements (règle 11) --------------------------------------------------


@transaction.atomic
def transfer(
    lot: Lot,
    *,
    from_location: Location,
    to_location: Location,
    quantity: Decimal,
    user=None,
    reason: str = "",
) -> str:
    """Déplace une quantité d'un lot d'un emplacement à un autre (sortie + entrée).

    Renvoie le numéro de transfert, commun aux deux mouvements.
    """
    lot = _lock(lot)
    if lot.status == LotStatus.DESTROYED:
        raise ValidationError(f"Le lot {lot.number} est détruit : il ne peut plus être déplacé.")
    if from_location.pk == to_location.pk:
        raise ValidationError({"to_location": "Choisis un emplacement différent."})
    if not to_location.active:
        raise ValidationError({"to_location": f"L'emplacement {to_location.code} est inactif."})
    if quantity <= 0:
        raise ValidationError({"quantity": "La quantité doit être positive."})
    available = quantity_at(lot, from_location)
    if quantity > available:
        raise ValidationError(
            {
                "quantity": f"Stock insuffisant : {available.normalize():f} {lot.unit} du lot "
                f"{lot.number} en {from_location.code}."
            }
        )
    check_location_compatible(lot.article, to_location)

    number = next_document_number(f"TR-{timezone.localdate().year}", 5)
    reason = reason.strip() or f"Transfert {from_location.code} → {to_location.code}"
    for movement_type, signed, location in (
        (MovementType.TRANSFER_OUT, -quantity, from_location),
        (MovementType.TRANSFER_IN, quantity, to_location),
    ):
        StockMovement.objects.create(
            lot=lot,
            movement_type=movement_type,
            quantity=signed,
            location=location,
            user=_user_or_none(user),
            reason=reason,
            reference=number,
        )
    return number


@transaction.atomic
def correct_movement(
    movement: StockMovement, *, reason: str, quantity: Decimal | None = None, user=None
) -> StockMovement:
    """Corrige une erreur de saisie par un mouvement inverse (on ne modifie jamais l'original).

    Sans `quantity`, annule tout ce qui reste du mouvement ; sinon, en corrige une partie
    (ex. 400 kg saisis au lieu de 40 kg : correction de 360 kg).
    """
    if not reason.strip():
        raise ValidationError({"reason": "Indique le motif de la correction."})
    if movement.movement_type != MovementType.RECEPTION:
        raise ValidationError(
            "Seul un mouvement de réception se corrige ainsi. Un transfert se corrige par "
            "un transfert dans l'autre sens."
        )
    lot = _lock(movement.lot)
    if lot.status == LotStatus.DESTROYED:
        raise ValidationError(f"Le lot {lot.number} est détruit.")

    already = movement.corrections.aggregate(total=Sum("quantity"))["total"] or ZERO
    correctable = movement.quantity + already  # les corrections sont de signe opposé
    amount = correctable if quantity is None else quantity
    if amount <= 0 or amount > correctable:
        raise ValidationError(
            {
                "quantity": f"La correction doit être comprise entre 0 et "
                f"{correctable.normalize():f} {lot.unit}."
            }
        )
    available = quantity_at(lot, movement.location)
    if amount > available:
        raise ValidationError(
            {
                "quantity": f"Seulement {available.normalize():f} {lot.unit} restent en "
                f"{movement.location.code} : déplace d'abord le stock ou corrige moins."
            }
        )
    return StockMovement.objects.create(
        lot=lot,
        movement_type=MovementType.CORRECTION,
        quantity=-amount,
        location=movement.location,
        user=_user_or_none(user),
        reason=reason.strip(),
        reference=movement.reference,
        corrected_movement=movement,
    )


# --- FEFO (règle 4) ---------------------------------------------------------


@dataclass
class FefoLine:
    lot: Lot
    location: Location
    available: Decimal
    take: Decimal


@dataclass
class FefoPlan:
    requested: Decimal
    lines: list[FefoLine]

    @property
    def covered(self) -> Decimal:
        return sum((line.take for line in self.lines), ZERO)

    @property
    def missing(self) -> Decimal:
        return max(self.requested - self.covered, ZERO)


def fefo_plan(
    article: Article,
    site: Site,
    quantity: Decimal,
    *,
    on_date: date | None = None,
    min_expiry_date: date | None = None,
) -> FefoPlan:
    """Propose les lots à utiliser, en commençant par ceux qui périment le premier (FEFO).

    Seuls les lots libérés et non périmés du site sont proposés. `min_expiry_date` permettra
    d'exclure les lots trop courts pour un client (règle 5, phase 7).
    """
    if quantity <= 0:
        raise ValidationError({"quantity": "La quantité doit être positive."})
    on_date = on_date or timezone.localdate()
    earliest = max(on_date, min_expiry_date) if min_expiry_date else on_date

    rows = (
        StockMovement.objects.filter(
            lot__article=article,
            lot__status=LotStatus.RELEASED,
            location__site=site,
        )
        .filter(Q(lot__expiry_date__isnull=True) | Q(lot__expiry_date__gte=earliest))
        .values("lot", "location")
        .annotate(available=Sum("quantity"))
        .filter(available__gt=0)
    )
    lots = Lot.objects.in_bulk({row["lot"] for row in rows})
    locations = Location.objects.in_bulk({row["location"] for row in rows})

    def order(row):
        lot = lots[row["lot"]]
        # Les lots sans date (emballages) passent après les lots datés, puis le plus ancien reçu
        return (lot.expiry_date or date.max, lot.reception_date or date.max, lot.number)

    plan = FefoPlan(requested=quantity, lines=[])
    remaining = quantity
    for row in sorted(rows, key=order):
        take = min(row["available"], remaining)
        plan.lines.append(
            FefoLine(
                lot=lots[row["lot"]],
                location=locations[row["location"]],
                available=row["available"],
                take=take,
            )
        )
        remaining -= take
        if remaining <= 0:
            break
    return plan


# --- État des stocks --------------------------------------------------------


def stock_summary(*, site: Site | None = None, article_type: str | None = None, search: str = ""):
    """Stock par article et par site, réparti par statut de lot."""
    movements = StockMovement.objects.all()
    if site:
        movements = movements.filter(location__site=site)
    if article_type:
        movements = movements.filter(lot__article__article_type=article_type)
    if search:
        movements = movements.filter(
            Q(lot__article__code__icontains=search) | Q(lot__article__name__icontains=search)
        )

    def total_for(status):
        return Sum("quantity", filter=Q(lot__status=status), default=ZERO)

    rows = (
        movements.values(
            "lot__article",
            "lot__article__code",
            "lot__article__name",
            "lot__article__unit",
            "location__site__code",
        )
        .annotate(
            released=total_for(LotStatus.RELEASED),
            quarantine=total_for(LotStatus.QUARANTINE),
            blocked=total_for(LotStatus.BLOCKED),
            total=Sum("quantity"),
        )
        .exclude(total=0)
        .order_by("lot__article__code", "location__site__code")
    )
    return [
        {
            "article": row["lot__article"],
            "article_code": row["lot__article__code"],
            "article_name": row["lot__article__name"],
            "unit": row["lot__article__unit"],
            "site_code": row["location__site__code"],
            "released": row["released"],
            "quarantine": row["quarantine"],
            "blocked": row["blocked"],
            "total": row["total"],
        }
        for row in rows
    ]
