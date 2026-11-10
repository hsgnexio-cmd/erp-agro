"""Plan de production hebdomadaire des produits finis (phase 9b).

Fiche entreprise : « plan hebdomadaire figé à J-2, MDD à la commande, marque Brévanne sur
stock ». Le plan de la semaine S+1 est calculé à partir de la prévision de vente, ajusté par
la production, puis figé le samedi à 12 h (J-2 avant le lundi) : le gel crée les ordres de
fabrication, jour par jour.

Calcul, produit par produit (décisions de la phase 9b) :
- demande = prévision de la semaine (dernière version figée qui la couvre) ; pour un produit
  MDD, la plus grande valeur entre la prévision et les commandes déjà reçues ;
- stock de sécurité (marque Brévanne seulement) = demande moyenne par jour × jours de
  sécurité de l'article (par défaut 1 jour, 0,5 jour si la durée de vie est ≤ 10 jours) ;
- stock projeté au lundi = stock disponible (lots libérés ou en quarantaine, non périmés)
  + OF à venir avant la semaine − demande prévue d'ici là (jamais négatif) ;
- à fabriquer = demande + stock de sécurité − stock projeté, arrondi au colis de 12 au-dessus,
  réparti à parts égales du lundi au vendredi, sur la première ligne compatible.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import ROUND_CEILING, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from previsions import forecast as sales_forecast
from previsions.models import ForecastVersion
from referentiel import calendar
from referentiel.calendar import Activity
from referentiel.choices import ArticleType
from referentiel.models import Article, ProductionLine
from referentiel.services import line_accepts
from stocks.choices import LotStatus
from stocks.models import StockMovement
from ventes.models import CustomerOrderLine
from ventes.models import OrderStatus as CustomerOrderStatus

from . import orders, planning
from .models import (
    MasterPlan,
    MasterPlanDay,
    MasterPlanItem,
    OrderStatus,
    PlanStatus,
    ProductionOrder,
)

ZERO = Decimal("0")
CASE_SIZE = Decimal("12")
WORK_DAYS = 5  # du lundi au vendredi (fiche entreprise : 5 jours sur 7)
DEFAULT_SAFETY_DAYS = Decimal("1")
SHORT_SAFETY_DAYS = Decimal("0.5")
SHORT_SHELF_LIFE_DAYS = 10
# Gel automatique : samedi 12 h, soit J-2 avant le lundi
FREEZE_WEEKDAY = 5
FREEZE_HOUR = 12


def week_start_moment(week: date) -> datetime:
    return timezone.make_aware(datetime.combine(week, time(0, 0)))


def work_days(week: date) -> list[date]:
    return [week + timedelta(days=offset) for offset in range(WORK_DAYS)]


def round_up_to_case(quantity: Decimal) -> Decimal:
    if quantity <= 0:
        return ZERO
    return (quantity / CASE_SIZE).to_integral_value(rounding=ROUND_CEILING) * CASE_SIZE


def closed_reason(day: date, line: ProductionLine) -> str:
    """Raison pour laquelle l'usine de la ligne ne fabrique pas ce jour-là (vide si ouvré)."""
    return calendar.closed_reason(day, Activity.PRODUCTION, line.site.code)


def production_days(week: date, line: ProductionLine) -> list[date]:
    """Jours ouvrés de l'usine de la ligne dans la semaine (hors fériés et fermetures)."""
    return [day for day in work_days(week) if not closed_reason(day, line)]


def split_over_days(quantity: Decimal, days: list[date]) -> dict[date, Decimal]:
    """Répartit une quantité (multiple de 12) à parts égales, le reste sur les premiers jours."""
    cases = int(quantity / CASE_SIZE)
    base, remainder = divmod(cases, len(days))
    return {
        day: (base + (1 if index < remainder else 0)) * CASE_SIZE for index, day in enumerate(days)
    }


def safety_days(article: Article) -> Decimal:
    """Jours de stock de sécurité : aucun pour un produit MDD (fabriqué à la commande)."""
    if article.brand_customer_id:
        return ZERO
    if article.safety_stock_days is not None:
        return article.safety_stock_days
    if (article.shelf_life_days or 0) <= SHORT_SHELF_LIFE_DAYS:
        return SHORT_SAFETY_DAYS
    return DEFAULT_SAFETY_DAYS


def default_line(article: Article) -> ProductionLine | None:
    for line in ProductionLine.objects.filter(active=True).order_by("code"):
        if line_accepts(line, article) is None:
            return line
    return None


# --- Données lues -------------------------------------------------------------------------


def forecast_version_for(week: date, at: datetime) -> ForecastVersion | None:
    """Dernière version de prévision figée (avant `at`) qui couvre la semaine."""
    return (
        ForecastVersion.objects.filter(
            created_at__lte=at,
            first_week__lte=week,
            first_week__gte=week - timedelta(days=7 * (sales_forecast.HORIZON_WEEKS - 1)),
        )
        .order_by("-created_at", "-id")
        .first()
    )


def forecast_by_article(week: date, at: datetime) -> tuple[ForecastVersion | None, dict]:
    """Prévision de la semaine par produit (toutes enseignes) : version figée, sinon calcul
    du moment."""
    version = forecast_version_for(week, at)
    totals: dict[int, Decimal] = defaultdict(lambda: ZERO)
    if version is not None:
        rows = (
            version.lines.filter(week=week).values("article_id").annotate(quantity=Sum("quantity"))
        )
        for row in rows:
            totals[row["article_id"]] += row["quantity"]
    else:
        for row in sales_forecast.compute(at):
            if row.week == week:
                totals[row.article.pk] += row.quantity
    return version, dict(totals)


def current_week_forecast(at: datetime) -> dict[int, Decimal]:
    """Prévision de la semaine en cours par produit (pour estimer la demande d'ici lundi)."""
    week = sales_forecast.current_week(at)
    version = forecast_version_for(week, at)
    if version is None:
        return {}
    rows = version.lines.filter(week=week).values("article_id").annotate(quantity=Sum("quantity"))
    return {row["article_id"]: row["quantity"] for row in rows}


def ordered_by_article(week: date) -> dict[int, Decimal]:
    rows = (
        CustomerOrderLine.objects.exclude(order__status=CustomerOrderStatus.CANCELLED)
        .filter(order__requested_delivery_date__range=(week, week + timedelta(days=6)))
        .values("article_id")
        .annotate(quantity=Sum("quantity"))
    )
    return {row["article_id"]: row["quantity"] for row in rows}


def available_stock_by_article(today: date) -> dict[int, Decimal]:
    """Lots libérés ou en quarantaine (la production de la veille attend sa libération),
    non périmés."""
    rows = (
        StockMovement.objects.filter(
            lot__article__article_type=ArticleType.FINISHED_PRODUCT,
            lot__status__in=[LotStatus.RELEASED, LotStatus.QUARANTINE],
            lot__expiry_date__gte=today,
        )
        .values("lot__article_id")
        .annotate(quantity=Sum("quantity"))
    )
    return {row["lot__article_id"]: row["quantity"] for row in rows if row["quantity"] > 0}


def open_orders_by_article(today: date, week: date) -> dict[int, Decimal]:
    """Reste à fabriquer des OF planifiés ou lancés d'ici la semaine du plan."""
    totals: dict[int, Decimal] = defaultdict(lambda: ZERO)
    pending = ProductionOrder.objects.filter(
        article__article_type=ArticleType.FINISHED_PRODUCT,
        status__in=[OrderStatus.PLANNED, OrderStatus.LAUNCHED],
        planned_date__gte=today,
        planned_date__lt=week,
    )
    for order in pending:
        remaining = order.planned_quantity - orders.produced_quantity(order)
        if remaining > 0:
            totals[order.article_id] += remaining
    return dict(totals)


# --- Calcul ------------------------------------------------------------------------------


@dataclass
class ItemCalculation:
    article: Article
    line: ProductionLine
    forecast_quantity: Decimal
    ordered_quantity: Decimal
    demand: Decimal
    safety_days: Decimal
    safety_stock: Decimal
    stock: Decimal
    open_orders: Decimal
    demand_before: Decimal
    projected_stock: Decimal
    proposed_quantity: Decimal


def calculate(week: date, at: datetime | None = None):
    """Calcul du plan (sans rien enregistrer) : version de prévision, produits, refus."""
    at = at or timezone.now()
    today = timezone.localtime(at).date()
    version, forecasts = forecast_by_article(week, at)
    ordered = ordered_by_article(week)
    stock = available_stock_by_article(today)
    open_orders = open_orders_by_article(today, week)
    this_week = current_week_forecast(at)
    days_before = max(0, (week - today).days)

    items, skipped = [], []
    articles = Article.objects.filter(
        article_type=ArticleType.FINISHED_PRODUCT, active=True
    ).select_related("recipe__family", "brand_customer")
    for article in articles.order_by("code"):
        forecast_quantity = forecasts.get(article.pk, ZERO)
        ordered_quantity = ordered.get(article.pk, ZERO)
        # MDD : à la commande ; les commandes reçues l'emportent si elles dépassent la prévision
        demand = (
            max(forecast_quantity, ordered_quantity)
            if article.brand_customer_id
            else forecast_quantity
        )
        if demand <= 0:
            continue
        line = default_line(article) if hasattr(article, "bom") else None
        if line is None:
            skipped.append(f"{article.code} : aucune ligne compatible ou pas de nomenclature.")
            continue
        days = safety_days(article)
        safety = (demand / 7 * days).to_integral_value(rounding=ROUND_CEILING)
        before = (this_week.get(article.pk, ZERO) / 7 * days_before).quantize(Decimal("1"))
        on_hand, coming = stock.get(article.pk, ZERO), open_orders.get(article.pk, ZERO)
        projected = max(ZERO, on_hand + coming - before)
        items.append(
            ItemCalculation(
                article=article,
                line=line,
                forecast_quantity=forecast_quantity,
                ordered_quantity=ordered_quantity,
                demand=demand,
                safety_days=days,
                safety_stock=safety,
                stock=on_hand,
                open_orders=coming,
                demand_before=before,
                projected_stock=projected,
                proposed_quantity=round_up_to_case(demand + safety - projected),
            )
        )
    return version, items, skipped


def _check_future_week(week: date, at: datetime) -> None:
    if week.weekday() != 0:
        raise ValidationError("Une semaine est désignée par son lundi.")
    if week <= sales_forecast.current_week(at):
        raise ValidationError("On ne planifie que les semaines à venir (à partir de S+1).")


def _locked_plan(plan: MasterPlan) -> MasterPlan:
    return MasterPlan.objects.select_for_update().get(pk=plan.pk)


def _check_draft(plan: MasterPlan) -> None:
    if plan.status != PlanStatus.DRAFT:
        raise ValidationError(
            "Ce plan est figé : il ne se modifie plus. Modifie les OF si nécessaire."
        )


def _user(user):
    return user if user is not None and user.is_authenticated else None


@transaction.atomic
def compute_plan(week: date, *, user=None, at: datetime | None = None):
    """Calcule (ou recalcule) le plan brouillon de la semaine. Renvoie (plan, refus)."""
    at = at or timezone.now()
    _check_future_week(week, at)
    plan = MasterPlan.objects.select_for_update().filter(week=week).first()
    if plan is not None:
        _check_draft(plan)
        plan.items.all().delete()  # les ajustements du brouillon sont recalculés
    version, items, skipped = calculate(week, at)
    if plan is None:
        plan = MasterPlan(week=week)
    plan.forecast_version = version
    plan.computed_at = at
    plan.computed_by = _user(user)
    plan.save()
    for calc in items:
        item = MasterPlanItem.objects.create(
            plan=plan,
            article=calc.article,
            line=calc.line,
            forecast_quantity=calc.forecast_quantity,
            ordered_quantity=calc.ordered_quantity,
            demand=calc.demand,
            safety_days=calc.safety_days,
            safety_stock=calc.safety_stock,
            stock=calc.stock,
            open_orders=calc.open_orders,
            demand_before=calc.demand_before,
            projected_stock=calc.projected_stock,
            proposed_quantity=calc.proposed_quantity,
        )
        # Phase 11 : réparti sur les jours ouvrés de l'usine ; zéro les jours fériés ou fermés
        open_days = production_days(week, calc.line) or work_days(week)
        split = split_over_days(calc.proposed_quantity, open_days)
        for day in work_days(week):
            MasterPlanDay.objects.create(item=item, day=day, quantity=split.get(day, ZERO))
    return plan, skipped


# --- Ajustements du brouillon ------------------------------------------------------------


@transaction.atomic
def set_quantity(plan: MasterPlan, *, article: Article, day: date, quantity: Decimal):
    """Ajuste la quantité d'un produit un jour donné (brouillon seulement)."""
    plan = _locked_plan(plan)
    _check_draft(plan)
    if day not in work_days(plan.week):
        raise ValidationError("L'usine fabrique du lundi au vendredi de la semaine du plan.")
    if quantity is None or quantity < 0:
        raise ValidationError({"quantity": "La quantité ne peut pas être négative."})
    item = plan.items.select_related("line__site").filter(article=article).first()
    if item is None:
        raise ValidationError(f"{article.code} n'est pas dans le plan : ajoute-le d'abord.")
    reason = closed_reason(day, item.line)
    if reason and quantity > 0:
        raise ValidationError(
            f"L'usine {item.line.site.code} ne fabrique pas le {calendar.describe(day)} ({reason})."
        )
    entry, _ = MasterPlanDay.objects.get_or_create(
        item=item, day=day, defaults={"quantity": quantity}
    )
    entry.quantity = quantity
    entry.save()
    return entry


@transaction.atomic
def set_line(plan: MasterPlan, *, article: Article, line: ProductionLine) -> MasterPlanItem:
    plan = _locked_plan(plan)
    _check_draft(plan)
    item = plan.items.filter(article=article).first()
    if item is None:
        raise ValidationError(f"{article.code} n'est pas dans le plan : ajoute-le d'abord.")
    refusal = line_accepts(line, article)
    if refusal:
        raise ValidationError({"line": f"Ligne refusée : {refusal}."})
    item.line = line
    item.save()
    return item


@transaction.atomic
def add_article(plan: MasterPlan, *, article: Article, line: ProductionLine | None = None):
    """Ajoute à la main un produit absent du calcul (quantités à saisir)."""
    plan = _locked_plan(plan)
    _check_draft(plan)
    if article.article_type != ArticleType.FINISHED_PRODUCT or not article.active:
        raise ValidationError({"article": "On ne planifie que des produits finis actifs."})
    if not hasattr(article, "bom"):
        raise ValidationError({"article": f"{article.code} n'a pas de nomenclature."})
    if plan.items.filter(article=article).exists():
        raise ValidationError(f"{article.code} est déjà dans le plan.")
    line = line or default_line(article)
    if line is None:
        raise ValidationError({"line": f"Aucune ligne compatible avec {article.code}."})
    refusal = line_accepts(line, article)
    if refusal:
        raise ValidationError({"line": f"Ligne refusée : {refusal}."})
    zero = dict.fromkeys(
        (
            "forecast_quantity", "ordered_quantity", "demand", "safety_days", "safety_stock",
            "stock", "open_orders", "demand_before", "projected_stock", "proposed_quantity",
        ),
        ZERO,
    )  # fmt: skip
    item = MasterPlanItem.objects.create(plan=plan, article=article, line=line, **zero)
    for day in work_days(plan.week):
        MasterPlanDay.objects.create(item=item, day=day, quantity=ZERO)
    return item


# --- Gel à J-2 ---------------------------------------------------------------------------


@transaction.atomic
def freeze_plan(plan: MasterPlan, *, user=None, at: datetime | None = None) -> MasterPlan:
    """Fige le plan et crée un OF planifié par produit et par jour."""
    at = at or timezone.now()
    plan = _locked_plan(plan)
    _check_draft(plan)
    if at >= week_start_moment(plan.week):
        raise ValidationError("La semaine a commencé : trop tard pour figer ce plan.")
    label = sales_forecast.week_label(plan.week)
    days = (
        MasterPlanDay.objects.filter(item__plan=plan, quantity__gt=0)
        .select_related("item__article", "item__line")
        .order_by("day", "item__line__code", "item__article__code")
    )
    for entry in days:
        entry.production_order = orders.create_order(
            article=entry.item.article,
            planned_quantity=entry.quantity,
            planned_date=entry.day,
            line=entry.item.line,
            comment=f"Plan de production {label} figé",
            user=user,
        )
        entry.save()
    plan.status = PlanStatus.FROZEN
    plan.frozen_at = at
    plan.frozen_by = _user(user)
    plan.save()
    return plan


def freeze_next_week(at: datetime | None = None) -> MasterPlan | None:
    """Tâche du samedi 12 h : calcule le plan de S+1 s'il n'existe pas, puis le fige."""
    at = at or timezone.now()
    week = sales_forecast.current_week(at) + timedelta(days=7)
    plan = MasterPlan.objects.filter(week=week).first()
    if plan is None:
        plan, _ = compute_plan(week, at=at)
    if plan.status == PlanStatus.FROZEN:
        return None
    return freeze_plan(plan, at=at)


# --- Lecture : charge des lignes et écarts après le gel ------------------------------------


def line_load(plan: MasterPlan) -> list[dict]:
    """Heures par ligne et par jour (quantité ÷ cadence), avec les surcharges."""
    hours: dict[tuple[int, date], Decimal] = defaultdict(lambda: ZERO)
    lines = {}
    for entry in MasterPlanDay.objects.filter(item__plan=plan).select_related("item__line"):
        line = entry.item.line
        lines[line.pk] = line
        hours[(line.pk, entry.day)] += entry.quantity / line.capacity_per_hour
    result = []
    for line in sorted(lines.values(), key=lambda value: value.code):
        cells = []
        for day in work_days(plan.week):
            value = hours[(line.pk, day)].quantize(Decimal("0.1"))
            closed = closed_reason(day, line)
            capacity = ZERO if closed else planning.DAILY_CAPACITY_HOURS
            cells.append(
                {"day": day, "hours": value, "overload": value > capacity, "closed": closed}
            )
        result.append({"line": line, "cells": cells})
    return result


def deviation(entry: MasterPlanDay) -> str:
    """Écart entre le plan figé et l'OF tel qu'il est aujourd'hui (vide si aucun)."""
    order = entry.production_order
    if order is None:
        return ""
    if order.status == OrderStatus.CANCELLED:
        return "OF annulé"
    changes = []
    if order.planned_quantity != entry.quantity:
        changes.append(f"quantité {order.planned_quantity.normalize():f}")
    if order.planned_date != entry.day:
        changes.append(f"déplacé au {order.planned_date:%d/%m}")
    if order.line_id != entry.item.line_id:
        changes.append(f"ligne {order.line.code if order.line else '—'}")
    return ", ".join(changes)
