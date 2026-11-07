"""Calcul des prévisions de vente (phase 9a).

Ce que l'on prévoit : la **demande**, c'est-à-dire les quantités commandées par les enseignes
(commandes non annulées), rangées par semaine de livraison demandée. On ne part pas des
expéditions : elles sont réduites par les ruptures, et la prévision baisserait à chaque
rupture.

Méthode (décision de la phase 9a) :
1. base = moyenne pondérée des 4 dernières semaines terminées (S-1 : 40 %, S-2 : 30 %,
   S-3 : 20 %, S-4 : 10 %). Une semaine en promotion est ramenée à son volume normal
   (divisée par le coefficient). Les semaines antérieures à la première commande du
   produit chez l'enseigne ne comptent pas ;
2. promotion annoncée sur la semaine : base × coefficient (au plus ×3) ;
3. correction manuelle du commercial : elle remplace la quantité calculée.
Chaque quantité est arrondie au colis de 12.

La prévision couvre les semaines S+1 à S+8. Elle est figée chaque lundi (et à la demande)
dans une version jamais modifiée, qui sert à mesurer la fiabilité à S-1.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Min, Q, Sum
from django.utils import timezone

from referentiel.choices import ArticleType
from referentiel.models import Article, Customer
from referentiel.services import next_document_number
from ventes.models import CustomerOrderLine, OrderStatus
from ventes.orders import orderable_refusal

from .models import (
    ForecastAdjustment,
    ForecastLine,
    ForecastVersion,
    Promotion,
    VersionSource,
)

ZERO = Decimal("0")
HORIZON_WEEKS = 8
# Poids des semaines S-1, S-2, S-3, S-4 dans la moyenne
HISTORY_WEIGHTS = (Decimal("40"), Decimal("30"), Decimal("20"), Decimal("10"))
CASE_SIZE = Decimal("12")
MAX_COEFFICIENT = Decimal("3")
# Fiche entreprise : promotions annoncées 6 à 8 semaines avant
MIN_NOTICE_DAYS = 42
ACCURACY_TARGET = Decimal("80")

Key = tuple[int, int, date]  # (enseigne, produit, lundi de la semaine)


# --- Semaines --------------------------------------------------------------------------


def monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def week_label(week: date) -> str:
    return f"S{week.isocalendar().week:02d}"


def week_start_moment(week: date) -> datetime:
    """Lundi 0 h, heure de Paris."""
    return timezone.make_aware(datetime.combine(week, time(0, 0)))


def current_week(at: datetime | None = None) -> date:
    return monday(timezone.localtime(at or timezone.now()).date())


def horizon(at: datetime | None = None) -> list[date]:
    """Les 8 semaines prévues : de la semaine prochaine (S+1) à S+8."""
    first = current_week(at) + timedelta(days=7)
    return [first + timedelta(days=7 * k) for k in range(HORIZON_WEEKS)]


def round_to_case(quantity: Decimal) -> Decimal:
    """Arrondi au colis de 12 le plus proche."""
    return (quantity / CASE_SIZE).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * CASE_SIZE


# --- Données lues ------------------------------------------------------------------------


def forecastable_pairs(customer_id: int | None = None) -> list[tuple[Customer, Article]]:
    """Couples enseigne × produit fini que l'enseigne peut commander."""
    customers = Customer.objects.filter(active=True).order_by("code")
    if customer_id is not None:
        customers = customers.filter(pk=customer_id)
    articles = list(
        Article.objects.filter(article_type=ArticleType.FINISHED_PRODUCT, active=True)
        .select_related("brand_customer")
        .order_by("code")
    )
    return [
        (customer, article)
        for customer in customers
        for article in articles
        if orderable_refusal(customer, article) is None
    ]


def _order_lines(customer_id: int | None = None):
    lines = CustomerOrderLine.objects.exclude(order__status=OrderStatus.CANCELLED)
    if customer_id is not None:
        lines = lines.filter(order__customer_id=customer_id)
    return lines


def demand_by_week(start: date, end: date, customer_id: int | None = None) -> dict[Key, Decimal]:
    """Quantités commandées par enseigne × produit × semaine de livraison, entre deux dates."""
    rows = (
        _order_lines(customer_id)
        .filter(order__requested_delivery_date__range=(start, end))
        .values("order__customer_id", "article_id", "order__requested_delivery_date")
        .annotate(quantity=Sum("quantity"))
    )
    demand: dict[Key, Decimal] = defaultdict(lambda: ZERO)
    for row in rows:
        key = (
            row["order__customer_id"],
            row["article_id"],
            monday(row["order__requested_delivery_date"]),
        )
        demand[key] += row["quantity"]
    return dict(demand)


def first_demand_weeks(customer_id: int | None = None) -> dict[tuple[int, int], date]:
    """Semaine de la première commande de chaque produit chez chaque enseigne."""
    rows = (
        _order_lines(customer_id)
        .values("order__customer_id", "article_id")
        .annotate(first=Min("order__requested_delivery_date"))
    )
    return {(row["order__customer_id"], row["article_id"]): monday(row["first"]) for row in rows}


def known_promotions(at: datetime, customer_id: int | None = None) -> list[Promotion]:
    """Promotions saisies et non annulées à l'instant `at`."""
    promotions = Promotion.objects.filter(created_at__lte=at).filter(
        Q(cancelled_at__isnull=True) | Q(cancelled_at__gt=at)
    )
    if customer_id is not None:
        promotions = promotions.filter(customer_id=customer_id)
    return list(promotions)


def _promotion_for(promotions: list[Promotion], customer_id, article_id, week) -> Promotion | None:
    for promotion in promotions:
        if (
            promotion.customer_id == customer_id
            and promotion.article_id == article_id
            and promotion.first_week <= week <= promotion.last_week
        ):
            return promotion
    return None


def latest_adjustments(
    at: datetime, weeks: list[date], customer_id: int | None = None
) -> dict[Key, ForecastAdjustment]:
    """Dernière correction saisie (avant `at`) pour chaque produit × enseigne × semaine."""
    adjustments = ForecastAdjustment.objects.filter(created_at__lte=at, week__in=weeks)
    if customer_id is not None:
        adjustments = adjustments.filter(customer_id=customer_id)
    latest = {}
    for adjustment in adjustments.select_related("created_by").order_by("created_at", "id"):
        latest[(adjustment.customer_id, adjustment.article_id, adjustment.week)] = adjustment
    return latest


# --- Calcul -----------------------------------------------------------------------------


@dataclass
class ForecastRow:
    customer: Customer
    article: Article
    week: date
    base_quantity: Decimal
    promotion: Promotion | None
    promo_quantity: Decimal | None
    adjustment: ForecastAdjustment | None
    quantity: Decimal

    @property
    def promo_coefficient(self) -> Decimal | None:
        return self.promotion.coefficient if self.promotion else None


def base_quantity(
    customer_id: int,
    article_id: int,
    history_weeks: list[date],
    demand: dict[Key, Decimal],
    first_week: date | None,
    promotions: list[Promotion],
) -> Decimal:
    """Moyenne pondérée des 4 dernières semaines, hors effet des promotions."""
    total = weights = ZERO
    for weight, week in zip(HISTORY_WEIGHTS, history_weeks, strict=True):
        if first_week is None or week < first_week:
            continue  # produit pas encore vendu à cette enseigne
        quantity = demand.get((customer_id, article_id, week), ZERO)
        promotion = _promotion_for(promotions, customer_id, article_id, week)
        if promotion:
            quantity = quantity / promotion.coefficient
        total += weight * quantity
        weights += weight
    return round_to_case(total / weights) if weights else ZERO


def compute(at: datetime | None = None, customer_id: int | None = None) -> list[ForecastRow]:
    """Prévision à 8 semaines telle qu'elle serait figée à l'instant `at` (défaut : maintenant)."""
    at = at or timezone.now()
    weeks = horizon(at)
    this_week = current_week(at)
    history_weeks = [this_week - timedelta(days=7 * (k + 1)) for k in range(len(HISTORY_WEIGHTS))]
    demand = demand_by_week(history_weeks[-1], this_week - timedelta(days=1), customer_id)
    firsts = first_demand_weeks(customer_id)
    promotions = known_promotions(at, customer_id)
    adjustments = latest_adjustments(at, weeks, customer_id)

    rows = []
    for customer, article in forecastable_pairs(customer_id):
        base = base_quantity(
            customer.pk,
            article.pk,
            history_weeks,
            demand,
            firsts.get((customer.pk, article.pk)),
            promotions,
        )
        for week in weeks:
            promotion = _promotion_for(promotions, customer.pk, article.pk, week)
            promo_quantity = round_to_case(base * promotion.coefficient) if promotion else None
            adjustment = adjustments.get((customer.pk, article.pk, week))
            if adjustment is not None and adjustment.quantity is None:
                adjustment = None  # correction annulée : retour au calcul
            if base == 0 and adjustment is None:
                continue
            if adjustment is not None:
                quantity = adjustment.quantity
            elif promo_quantity is not None:
                quantity = promo_quantity
            else:
                quantity = base
            rows.append(
                ForecastRow(
                    customer, article, week, base, promotion, promo_quantity, adjustment, quantity
                )
            )
    return rows


@transaction.atomic
def create_version(
    *,
    user=None,
    source: str = VersionSource.MANUAL,
    comment: str = "",
    at: datetime | None = None,
) -> ForecastVersion:
    """Fige la prévision du moment dans une nouvelle version (numéro PRV-AAAA-NNNNN)."""
    at = at or timezone.now()
    rows = compute(at)
    version = ForecastVersion.objects.create(
        number=next_document_number(f"PRV-{timezone.localtime(at).year}", 5),
        created_at=at,
        created_by=user if user is not None and user.is_authenticated else None,
        source=source,
        first_week=horizon(at)[0],
        comment=comment.strip(),
    )
    # Lignes calculées ci-dessus, jamais saisies : création groupée
    ForecastLine.objects.bulk_create(
        ForecastLine(
            version=version,
            customer=row.customer,
            article=row.article,
            week=row.week,
            base_quantity=row.base_quantity,
            promotion=row.promotion,
            promo_coefficient=row.promo_coefficient,
            adjustment=row.adjustment,
            quantity=row.quantity,
        )
        for row in rows
    )
    return version


def freeze_weekly(at: datetime | None = None) -> ForecastVersion | None:
    """Version automatique du lundi ; rien si elle existe déjà pour ce jour."""
    at = at or timezone.now()
    day = timezone.localtime(at).date()
    already = ForecastVersion.objects.filter(
        source=VersionSource.AUTOMATIC,
        created_at__gte=week_start_moment(day),
        created_at__lt=week_start_moment(day + timedelta(days=1)),
    )
    if already.exists():
        return None
    return create_version(source=VersionSource.AUTOMATIC, at=at)


# --- Promotions --------------------------------------------------------------------------


def validate_promotion(promotion: Promotion) -> None:
    """Règles vérifiées à chaque enregistrement d'une promotion."""
    errors = {}
    for field in ("first_week", "last_week"):
        value = getattr(promotion, field)
        if value and value.weekday() != 0:
            errors[field] = "Une semaine est désignée par son lundi."
    if promotion.first_week and promotion.last_week and promotion.last_week < promotion.first_week:
        errors["last_week"] = "La dernière semaine précède la première."
    if promotion.announced_on and promotion.first_week:
        if promotion.announced_on > promotion.first_week:
            errors["announced_on"] = "La promotion est annoncée après son début."
    if promotion.customer_id and promotion.article_id:
        reason = orderable_refusal(promotion.customer, promotion.article)
        if reason:
            errors["article"] = reason
    if errors:
        raise ValidationError(errors)
    if promotion.cancelled_at is None:
        overlap = (
            Promotion.objects.filter(
                customer_id=promotion.customer_id,
                article_id=promotion.article_id,
                cancelled_at__isnull=True,
                first_week__lte=promotion.last_week,
                last_week__gte=promotion.first_week,
            )
            .exclude(pk=promotion.pk)
            .first()
        )
        if overlap:
            raise ValidationError(
                f"Une promotion ×{overlap.coefficient} est déjà prévue sur cette période "
                f"({week_label(overlap.first_week)} à {week_label(overlap.last_week)}) : "
                "annule-la d'abord."
            )


@transaction.atomic
def create_promotion(
    *,
    customer: Customer,
    article: Article,
    first_week: date,
    last_week: date,
    coefficient: Decimal,
    announced_on: date | None = None,
    comment: str = "",
    user=None,
) -> Promotion:
    today = timezone.localdate()
    announced_on = announced_on or today
    errors = []
    if announced_on > today:
        errors.append("La date d'annonce ne peut pas être dans le futur.")
    if first_week < current_week() + timedelta(days=7):
        errors.append("Une promotion commence au plus tôt la semaine prochaine.")
    if errors:
        raise ValidationError(errors)
    return Promotion.objects.create(
        customer=customer,
        article=article,
        first_week=first_week,
        last_week=last_week,
        coefficient=coefficient,
        announced_on=announced_on,
        comment=comment.strip(),
        created_by=user if user is not None and user.is_authenticated else None,
    )


@transaction.atomic
def cancel_promotion(promotion: Promotion, *, reason: str, user=None) -> Promotion:
    promotion = Promotion.objects.select_for_update().get(pk=promotion.pk)
    if promotion.is_cancelled:
        raise ValidationError("Cette promotion est déjà annulée.")
    if promotion.first_week <= current_week():
        raise ValidationError("Une promotion commencée ne s'annule plus.")
    if not (reason or "").strip():
        raise ValidationError({"reason": "Indique le motif de l'annulation."})
    promotion.cancelled_at = timezone.now()
    promotion.cancelled_by = user if user is not None and user.is_authenticated else None
    promotion.cancel_reason = reason.strip()
    promotion.save()
    return promotion


# --- Corrections manuelles -------------------------------------------------------------------


def create_adjustment(
    *,
    customer: Customer,
    article: Article,
    week: date,
    quantity: Decimal | None,
    reason: str,
    user=None,
) -> ForecastAdjustment:
    errors = []
    if week not in horizon():
        errors.append("La semaine doit faire partie de l'horizon de prévision (S+1 à S+8).")
    refusal = orderable_refusal(customer, article)
    if refusal:
        errors.append(refusal)
    if errors:
        raise ValidationError(errors)
    return ForecastAdjustment.objects.create(
        customer=customer,
        article=article,
        week=week,
        quantity=quantity,
        reason=(reason or "").strip(),
        created_by=user if user is not None and user.is_authenticated else None,
    )


# --- Fiabilité à S-1 ---------------------------------------------------------------------


def s1_version(week: date) -> ForecastVersion | None:
    """Dernière version figée avant le lundi de la semaine, et qui la couvre."""
    return (
        ForecastVersion.objects.filter(
            created_at__lt=week_start_moment(week),
            first_week__lte=week,
            first_week__gte=week - timedelta(days=7 * (HORIZON_WEEKS - 1)),
        )
        .order_by("-created_at", "-id")
        .first()
    )


@dataclass
class WeekAccuracy:
    week: date
    version: ForecastVersion
    forecast: Decimal
    actual: Decimal
    abs_error: Decimal
    complete: bool

    @property
    def accuracy(self) -> Decimal | None:
        return accuracy_pct(self.abs_error, self.actual)


def accuracy_pct(abs_error: Decimal, actual: Decimal) -> Decimal | None:
    """1 − écart absolu ÷ commandes réelles, en %, jamais sous 0."""
    if not actual:
        return None
    value = (1 - Decimal(abs_error) / Decimal(actual)) * 100
    return max(ZERO, value).quantize(Decimal("0.1"))


def week_accuracy(week: date, customer_id: int | None = None) -> WeekAccuracy | None:
    """Prévision figée à S-1 comparée aux commandes de la semaine, produit × enseigne."""
    version = s1_version(week)
    if version is None:
        return None
    lines = version.lines.filter(week=week)
    if customer_id is not None:
        lines = lines.filter(customer_id=customer_id)
    forecast = {(line.customer_id, line.article_id): line.quantity for line in lines}
    actual = {
        (customer, article): quantity
        for (customer, article, _), quantity in demand_by_week(
            week, week + timedelta(days=6), customer_id
        ).items()
    }
    keys = forecast.keys() | actual.keys()
    abs_error = sum((abs(forecast.get(k, ZERO) - actual.get(k, ZERO)) for k in keys), ZERO)
    return WeekAccuracy(
        week=week,
        version=version,
        forecast=sum(forecast.values(), ZERO),
        actual=sum(actual.values(), ZERO),
        abs_error=abs_error,
        complete=week + timedelta(days=6) < timezone.localdate(),
    )


def accuracy_by_week(start: date, end: date, customer_id: int | None = None) -> list[WeekAccuracy]:
    """Fiabilité de chaque semaine touchant la période (seules les semaines avec version S-1)."""
    results = []
    week = monday(start)
    while week <= end:
        result = week_accuracy(week, customer_id)
        if result is not None:
            results.append(result)
        week += timedelta(days=7)
    return results


def overall_accuracy(results: list[WeekAccuracy]) -> Decimal | None:
    """Fiabilité de plusieurs semaines terminées : somme des écarts ÷ somme des commandes."""
    complete = [result for result in results if result.complete]
    return accuracy_pct(
        sum((r.abs_error for r in complete), ZERO), sum((r.actual for r in complete), ZERO)
    )
