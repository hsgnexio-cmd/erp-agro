"""Calcul des besoins (MRP) et propositions de commandes d'achat (phase 9c).

Horizon : la semaine en cours et les 8 suivantes, semaine par semaine (le lundi).

1. Production prévue, en produits finis :
   - OF planifiés ou lancés à partir d'aujourd'hui (reste à fabriquer) : semaine en cours et
     semaines dont le plan est figé ;
   - plan brouillon de la semaine, s'il existe ;
   - sinon, prévision de vente de la semaine (dernière version figée qui la couvre).
2. Éclatement des nomenclatures à tous les niveaux, pertes comprises : les semi-finis sont
   d'abord diminués de leur stock disponible, puis éclatés en matières et emballages.
3. Besoin net, semaine par semaine, pour chaque matière et emballage :
   stock projeté = stock disponible (lots libérés ou en quarantaine, non périmés)
                   + commandes fournisseurs en cours (reste à recevoir, brouillons compris)
                   − besoins bruts cumulés ;
   dès qu'il devient négatif, une commande est proposée pour la semaine du besoin.
4. Proposition : fournisseur principal audité (sinon un autre fournisseur audité), quantité
   relevée au minimum de commande, date de commande = lundi de la semaine du besoin (ou
   aujourd'hui) − délai du fournisseur ; « en retard » si cette date est passée.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_CEILING, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from previsions.forecast import current_week, week_label
from production import master_plan
from production.models import MasterPlan, MasterPlanDay, OrderStatus, PlanStatus, ProductionOrder
from production.orders import produced_quantity, theoretical_needs
from referentiel.choices import ArticleType, SiteType, Unit
from referentiel.models import Article, Site, SupplierArticle
from stocks.choices import LotStatus
from stocks.models import StockMovement

from .choices import PurchaseOrderStatus
from .models import PurchaseOrderLine
from .services import create_purchase_order, current_price

ZERO = Decimal("0")
HORIZON_WEEKS = 8
OPEN_PURCHASE_STATUSES = [
    PurchaseOrderStatus.DRAFT,
    PurchaseOrderStatus.SENT,
    PurchaseOrderStatus.PARTIAL,
]
PURCHASED_TYPES = [ArticleType.RAW_MATERIAL, ArticleType.PACKAGING]
COMMENT = "Proposition du calcul des besoins (MRP)"

Gross = dict[int, dict[date, Decimal]]  # article → semaine → quantité


def horizon(today: date) -> list[date]:
    """Semaine en cours puis les 8 suivantes."""
    first = current_week()
    return [first + timedelta(days=7 * k) for k in range(HORIZON_WEEKS + 1)]


def _add(target: Gross, article_id: int, week: date, quantity: Decimal) -> None:
    if quantity > 0:
        target.setdefault(article_id, defaultdict(lambda: ZERO))[week] += quantity


# --- 1. Production prévue ---------------------------------------------------------------


@dataclass
class Sources:
    """D'où vient la production prévue de chaque semaine (affiché à l'écran)."""

    by_week: dict[date, str] = field(default_factory=dict)


def planned_production(weeks: list[date], today: date) -> tuple[Gross, Sources]:
    """Quantités de produits finis et semi-finis à fabriquer, par semaine."""
    production: Gross = {}
    sources = Sources()
    # OF ouverts : ce qui reste à fabriquer
    open_orders = ProductionOrder.objects.filter(
        status__in=[OrderStatus.PLANNED, OrderStatus.LAUNCHED],
        planned_date__gte=today,
        planned_date__lte=weeks[-1] + timedelta(days=6),
    )
    for order in open_orders:
        remaining = order.planned_quantity - produced_quantity(order)
        _add(production, order.article_id, master_plan_week(order.planned_date), remaining)

    plans = {plan.week: plan for plan in MasterPlan.objects.filter(week__in=weeks)}
    for week in weeks:
        plan = plans.get(week)
        if week == weeks[0]:
            sources.by_week[week] = "OF de la semaine"
        elif plan is not None and plan.status == PlanStatus.FROZEN:
            sources.by_week[week] = "OF du plan figé"
        elif plan is not None:
            sources.by_week[week] = "plan brouillon"
            days = MasterPlanDay.objects.filter(item__plan=plan).values("item__article_id")
            for row in days.annotate(quantity=Sum("quantity")):
                _add(production, row["item__article_id"], week, row["quantity"])
        else:
            version, forecasts = master_plan.forecast_by_article(week, timezone.now())
            sources.by_week[week] = (
                f"prévision {version.number}" if version else "prévision du moment"
            )
            for article_id, quantity in forecasts.items():
                _add(production, article_id, week, quantity)
    return production, sources


def master_plan_week(day: date) -> date:
    return day - timedelta(days=day.weekday())


# --- 2. Éclatement des nomenclatures ---------------------------------------------------------


class Explosion:
    """Besoins par unité de chaque article fabriqué (mis en cache), pertes comprises."""

    def __init__(self):
        self.cache: dict[int, list[tuple[Article, Decimal]]] = {}
        self.articles = {
            article.pk: article
            for article in Article.objects.select_related("bom").filter(
                article_type__in=[ArticleType.FINISHED_PRODUCT, ArticleType.SEMI_FINISHED]
            )
        }

    def per_unit(self, article_id: int) -> list[tuple[Article, Decimal]]:
        if article_id not in self.cache:
            article = self.articles.get(article_id)
            if article is None or not hasattr(article, "bom"):
                self.cache[article_id] = []
            else:
                self.cache[article_id] = [
                    (need.component, need.gross / 1_000)
                    for need in theoretical_needs(article, Decimal("1000"))
                ]
        return self.cache[article_id]


def available_stock(article_types: list[str], today: date) -> dict[int, Decimal]:
    rows = (
        StockMovement.objects.filter(
            lot__article__article_type__in=article_types,
            lot__status__in=[LotStatus.RELEASED, LotStatus.QUARANTINE],
        )
        .exclude(lot__expiry_date__lt=today)
        .values("lot__article_id")
        .annotate(quantity=Sum("quantity"))
    )
    return {row["lot__article_id"]: row["quantity"] for row in rows if row["quantity"] > 0}


def explode(production: Gross, weeks: list[date], today: date) -> tuple[Gross, dict]:
    """Besoins bruts en matières et emballages par semaine, avec le détail des semi-finis."""
    explosion = Explosion()
    semi_finished: Gross = {}
    purchased: Gross = {}

    def spread(source: Gross):
        for article_id, by_week in source.items():
            for week, quantity in by_week.items():
                for component, per_unit in explosion.per_unit(article_id):
                    need = per_unit * quantity
                    if component.article_type == ArticleType.SEMI_FINISHED:
                        _add(semi_finished, component.pk, week, need)
                    elif component.article_type in PURCHASED_TYPES:
                        _add(purchased, component.pk, week, need)

    finished = {
        article_id: by_week
        for article_id, by_week in production.items()
        if explosion.articles.get(article_id)
        and explosion.articles[article_id].article_type == ArticleType.FINISHED_PRODUCT
    }
    spread(finished)
    # Semi-finis : besoins des produits finis + OF de semi-finis déjà prévus, moins leur stock
    for article_id, by_week in production.items():
        if article_id not in finished:
            for week, quantity in by_week.items():
                _add(semi_finished, article_id, week, quantity)
    stock = available_stock([ArticleType.SEMI_FINISHED], today)
    netted: Gross = {}
    for article_id, by_week in semi_finished.items():
        remaining = stock.get(article_id, ZERO)
        for week in weeks:
            need = by_week.get(week, ZERO)
            used = min(remaining, need)
            remaining -= used
            _add(netted, article_id, week, need - used)
    spread(netted)
    return purchased, {"semi_finished": semi_finished}


# --- 3 et 4. Besoins nets et propositions --------------------------------------------------


def open_receipts(today: date, weeks: list[date]) -> Gross:
    """Reste à recevoir des commandes en cours, par semaine de livraison prévue.

    Une livraison en retard (prévue avant aujourd'hui) compte dans la semaine en cours."""
    receipts: Gross = {}
    lines = PurchaseOrderLine.objects.filter(
        order__status__in=OPEN_PURCHASE_STATUSES
    ).select_related("order")
    for line in lines:
        remaining = line.quantity - line.received_quantity
        expected = line.order.expected_delivery_date or line.order.order_date
        week = max(weeks[0], master_plan_week(expected))
        if week <= weeks[-1]:
            _add(receipts, line.article_id, week, remaining)
    return receipts


def choose_supplier(article: Article) -> SupplierArticle | None:
    """Fournisseur principal s'il est audité et actif, sinon un autre fournisseur audité."""
    links = (
        SupplierArticle.objects.filter(
            article=article, supplier__audited=True, supplier__active=True
        )
        .select_related("supplier")
        .order_by("-is_main_supplier", "supplier__lead_time_days", "supplier__code")
    )
    return links.first()


@dataclass
class WeekRow:
    week: date
    gross: Decimal
    receipts: Decimal
    projected: Decimal
    planned: Decimal


@dataclass
class Proposal:
    article: Article
    link: SupplierArticle | None
    week: date
    need_date: date
    order_date: date | None
    late: bool
    net: Decimal
    quantity: Decimal
    raised_to_minimum: bool
    unit_price: Decimal | None

    @property
    def amount(self) -> Decimal | None:
        if self.unit_price is None:
            return None
        return (self.quantity * self.unit_price).quantize(Decimal("0.01"))


@dataclass
class ArticleNeeds:
    article: Article
    stock: Decimal
    weeks: list[WeekRow]
    proposals: list[Proposal]


@dataclass
class MrpResult:
    weeks: list[date]
    sources: dict[date, str]
    articles: list[ArticleNeeds]

    @property
    def proposals(self) -> list[Proposal]:
        return sorted(
            (p for row in self.articles for p in row.proposals),
            key=lambda p: (p.order_date or date.min, p.article.code),
        )


def compute(today: date | None = None) -> MrpResult:
    today = today or timezone.localdate()
    weeks = horizon(today)
    production, sources = planned_production(weeks, today)
    gross, _ = explode(production, weeks, today)
    receipts = open_receipts(today, weeks)
    stock = available_stock(PURCHASED_TYPES, today)

    articles = Article.objects.filter(pk__in=set(gross) | set(receipts)).order_by("code")
    result = []
    for article in articles:
        link = choose_supplier(article)
        projected = stock.get(article.pk, ZERO)
        rows, proposals = [], []
        for week in weeks:
            need = gross.get(article.pk, {}).get(week, ZERO).quantize(Decimal("0.001"))
            coming = receipts.get(article.pk, {}).get(week, ZERO)
            projected += coming - need
            planned = ZERO
            if projected < 0:
                net = -projected
                minimum = link.min_order_quantity if link else None
                # Un article compté à l'unité (emballages) se commande en unités entières
                rounded = (
                    net.to_integral_value(rounding=ROUND_CEILING)
                    if article.unit == Unit.UNIT
                    else net
                )
                quantity = max(rounded, minimum or ZERO)
                need_date = max(today, week)
                order_date = (
                    need_date - timedelta(days=link.supplier.lead_time_days) if link else None
                )
                price = current_price(link, today) if link else None
                proposals.append(
                    Proposal(
                        article=article,
                        link=link,
                        week=week,
                        need_date=need_date,
                        order_date=order_date,
                        late=order_date is not None and order_date < today,
                        net=net,
                        quantity=quantity,
                        raised_to_minimum=quantity > rounded,
                        unit_price=price.unit_price if price else None,
                    )
                )
                planned = quantity
                projected += quantity
            rows.append(WeekRow(week, need, coming, projected, planned))
        result.append(ArticleNeeds(article, stock.get(article.pk, ZERO), rows, proposals))
    return MrpResult(weeks=weeks, sources=sources.by_week, articles=result)


# --- Création des commandes ------------------------------------------------------------------


def delivery_site() -> Site:
    """Les matières et emballages sont livrés à l'entrepôt (MPE)."""
    site = Site.objects.filter(site_type=SiteType.WAREHOUSE, active=True).order_by("code").first()
    if site is None:
        raise ValidationError("Aucun entrepôt actif pour recevoir les commandes.")
    return site


@transaction.atomic
def create_orders(selections: list[dict], *, user=None) -> list:
    """Crée une commande brouillon par fournisseur et par semaine de besoin.

    Chaque sélection : article, week (lundi de la semaine du besoin), quantity. La livraison
    est prévue pour la semaine du besoin, ou au plus tôt après le délai du fournisseur.
    """
    if not selections:
        raise ValidationError("Sélectionne au moins une proposition.")
    today = timezone.localdate()
    groups: dict[tuple[int, date], list[dict]] = defaultdict(list)
    suppliers = {}
    errors = []
    seen = set()
    for selection in selections:
        article, week, quantity = selection["article"], selection["week"], selection["quantity"]
        if (article.pk, week) in seen:
            errors.append(f"{article.code} : sélectionné deux fois pour la même semaine.")
            continue
        seen.add((article.pk, week))
        if article.article_type not in PURCHASED_TYPES:
            errors.append(f"{article.code} : seules les matières et les emballages s'achètent.")
            continue
        if week.weekday() != 0:
            errors.append(f"{article.code} : une semaine est désignée par son lundi.")
            continue
        if quantity is None or quantity <= 0:
            errors.append(f"{article.code} : la quantité doit être positive.")
            continue
        link = choose_supplier(article)
        if link is None:
            errors.append(f"{article.code} : aucun fournisseur audité ne le référence.")
            continue
        suppliers[link.supplier_id] = link.supplier
        groups[(link.supplier_id, week)].append({"article": article, "quantity": quantity})
    if errors:
        raise ValidationError(errors)
    site = delivery_site()
    created = []
    for (supplier_id, week), lines in sorted(
        groups.items(), key=lambda item: (item[0][1], suppliers[item[0][0]].code)
    ):
        supplier = suppliers[supplier_id]
        earliest = today + timedelta(days=supplier.lead_time_days)
        created.append(
            create_purchase_order(
                supplier=supplier,
                delivery_site=site,
                order_date=today,
                expected_delivery_date=max(earliest, week),
                comment=f"{COMMENT}, besoin de la semaine {week_label(week)}",
                lines=lines,
                user=user if user is not None and user.is_authenticated else None,
            )
        )
    return created
