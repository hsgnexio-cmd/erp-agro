"""Ordres de fabrication : création, lancement, déclaration FEFO, rendement, clôture.

La déclaration s'appuie sur `services.record_production` (phase 5), qui crée le lot fabriqué
et les consommations reliées : la traçabilité (règle 1) reste garantie.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from referentiel.choices import ArticleType, SiteType
from referentiel.models import Article, Location, ProductionLine, Site
from referentiel.services import line_accepts, next_document_number
from stocks import services as stock_services
from stocks.choices import AlertLevel, AlertType, MovementType
from stocks.models import StockMovement
from stocks.monitoring import raise_alert

from . import services
from .models import OrderStatus, ProductionDeclaration, ProductionOrder

# Objectif de rendement matière de la fiche entreprise
YIELD_TARGET = Decimal("96")
# Unités prises en compte dans le rendement matière (les emballages, en unités, à part)
MASS_UNITS = ("kg", "l")
UNLIMITED = Decimal("1000000000")
ZERO = Decimal("0")


def _user(user):
    return user if user is not None and user.is_authenticated else None


# --- Besoins théoriques ---------------------------------------------------------


@dataclass
class Need:
    component: Article
    net: Decimal
    gross: Decimal  # avec les pertes : ce qu'il faut sortir du stock
    unit: str


def theoretical_needs(article: Article, quantity: Decimal) -> list[Need]:
    """Besoins en composants pour fabriquer `quantity` de l'article (nomenclature + pertes)."""
    bom = article.bom
    factor = quantity / bom.base_quantity
    needs = []
    for line in bom.lines.select_related("component"):
        net = line.quantity * factor
        gross = net / (1 - line.loss_rate / Decimal(100))
        needs.append(
            Need(
                component=line.component,
                net=net.quantize(Decimal("0.001")),
                gross=gross.quantize(Decimal("0.001")),
                unit=line.unit,
            )
        )
    return needs


# --- Création et vie de l'OF ---------------------------------------------------------


def default_output_location(article: Article, site: Site) -> Location:
    """Semi-fini → chambre froide des semi-finis de l'usine ; produit fini → quarantaine PFN."""
    code = f"{site.code}-CF-SF" if article.article_type == ArticleType.SEMI_FINISHED else "PFN-QUAR"
    location = Location.objects.filter(code=code, active=True).first()
    if location is None:
        raise ValidationError(f"Emplacement de sortie {code} introuvable dans le référentiel.")
    return location


def _check_order(
    article: Article, quantity: Decimal, line: ProductionLine | None, site: Site | None
):
    """Vérifie les règles d'un OF et renvoie l'usine."""
    if article.article_type not in (ArticleType.SEMI_FINISHED, ArticleType.FINISHED_PRODUCT):
        raise ValidationError(
            {"article": "On ne fabrique que des semi-finis et des produits finis."}
        )
    if not hasattr(article, "bom"):
        raise ValidationError({"article": f"{article.code} n'a pas de nomenclature."})
    if not article.active:
        raise ValidationError({"article": f"{article.code} est inactif."})
    if quantity is None or quantity <= 0:
        raise ValidationError({"planned_quantity": "La quantité prévue doit être positive."})

    if article.article_type == ArticleType.FINISHED_PRODUCT:
        if line is None:
            raise ValidationError({"line": "Choisis la ligne de conditionnement du produit fini."})
        refusal = line_accepts(line, article)
        if refusal:
            raise ValidationError({"line": f"Ligne refusée : {refusal}."})
        if site is not None and site.pk != line.site_id:
            raise ValidationError({"site": f"La ligne {line.code} est à l'usine {line.site.code}."})
        return line.site
    if line is not None:
        raise ValidationError({"line": "Un semi-fini se prépare en cuisine, sans ligne."})
    if site is None or site.site_type != SiteType.FACTORY:
        raise ValidationError({"site": "Choisis l'usine qui prépare ce semi-fini."})
    return site


@transaction.atomic
def create_order(
    *,
    article: Article,
    planned_quantity: Decimal,
    planned_date: date,
    line: ProductionLine | None = None,
    site: Site | None = None,
    sequence: int = 1,
    comment: str = "",
    user=None,
) -> ProductionOrder:
    site = _check_order(article, planned_quantity, line, site)
    return ProductionOrder.objects.create(
        number=next_document_number(f"OF-{planned_date.year}", 5),
        article=article,
        planned_quantity=planned_quantity,
        planned_date=planned_date,
        sequence=sequence,
        site=site,
        line=line,
        output_location=default_output_location(article, site),
        comment=comment.strip(),
        created_by=_user(user),
    )


@transaction.atomic
def update_order(order: ProductionOrder, **fields) -> ProductionOrder:
    """Modifie un OF planifié (quantité, date, ligne, ordre dans la journée, commentaire)."""
    order = ProductionOrder.objects.select_for_update().get(pk=order.pk)
    if order.status != OrderStatus.PLANNED:
        raise ValidationError("Seul un OF planifié peut être modifié.")
    for name, value in fields.items():
        setattr(order, name, value)
    order.site = _check_order(order.article, order.planned_quantity, order.line, order.site)
    order.save()
    return order


def _locked(order: ProductionOrder) -> ProductionOrder:
    return ProductionOrder.objects.select_for_update().get(pk=order.pk)


@transaction.atomic
def launch_order(order: ProductionOrder, *, user=None) -> ProductionOrder:
    order = _locked(order)
    if order.status != OrderStatus.PLANNED:
        raise ValidationError("Seul un OF planifié peut être lancé.")
    order.status = OrderStatus.LAUNCHED
    order.launched_at = timezone.now()
    order.save()
    return order


@transaction.atomic
def cancel_order(order: ProductionOrder, *, user=None) -> ProductionOrder:
    order = _locked(order)
    if order.status not in (OrderStatus.PLANNED, OrderStatus.LAUNCHED):
        raise ValidationError(
            f"Un OF {order.get_status_display().lower()} ne peut pas être annulé."
        )
    if order.declarations.exists():
        raise ValidationError(
            "Une production a déjà été déclarée : clôture l'OF au lieu de l'annuler."
        )
    order.status = OrderStatus.CANCELLED
    order.closed_at = timezone.now()
    order.closed_by = _user(user)
    order.save()
    return order


# --- Proposition FEFO et déclaration (règle 4) ----------------------------------------


def proposal(order: ProductionOrder, quantity: Decimal) -> list[dict]:
    """Pour chaque composant : besoin brut et lots disponibles dans l'ordre FEFO, pré-remplis."""
    if quantity <= 0:
        raise ValidationError({"quantity": "La quantité à produire doit être positive."})
    result = []
    for need in theoretical_needs(order.article, quantity):
        plan = stock_services.fefo_plan(need.component, order.site, UNLIMITED)
        remaining = need.gross
        lots = []
        for line in plan.lines:
            suggested = min(line.available, max(remaining, ZERO))
            remaining -= suggested
            lots.append(
                {"lot": line.lot, "location": line.location, "available": line.available,
                 "suggested": suggested}
            )  # fmt: skip
        result.append({"need": need, "lots": lots, "missing": max(remaining, ZERO)})
    return result


@transaction.atomic
def declare_production(
    order: ProductionOrder,
    *,
    quantity: Decimal,
    consumptions: list[dict],
    production_date: date | None = None,
    comment: str = "",
    run_start: datetime | None = None,
    run_end: datetime | None = None,
    scrap_quantity: Decimal = ZERO,
    scrap_reason: str = "",
    require_run: bool = False,
    user=None,
) -> ProductionDeclaration:
    """Déclare une production sur un OF lancé.

    Chaque consommation : lot, location, quantity, et justification si le lot n'est pas
    celui proposé par le FEFO. Phase 10 : plage de marche de la ligne (obligatoire avec
    `require_run`, comme dans l'application) et quantité rebutée, pour le calcul du TRS.
    """
    from . import oee

    order = _locked(order)
    if order.status != OrderStatus.LAUNCHED:
        raise ValidationError("Seul un OF lancé peut recevoir une déclaration de production.")
    run_errors = oee.check_run(order, run_start, run_end, required=require_run)
    run_errors += oee.check_scrap(scrap_quantity, scrap_reason)
    if run_errors:
        raise ValidationError({"run": run_errors})
    consumptions = [c for c in consumptions if c["quantity"] and c["quantity"] > 0]

    errors, deviations = [], []
    totals: dict[int, Decimal] = {}
    for data in consumptions:
        if data["location"].site_id != order.site_id:
            errors.append(
                f"Lot {data['lot'].number} : l'emplacement {data['location'].code} n'est pas à "
                f"l'usine {order.site.code}."
            )
        totals[data["lot"].article_id] = totals.get(data["lot"].article_id, ZERO) + data["quantity"]

    # Règle 4 : les lots consommés doivent être ceux qui périment le premier
    for data in consumptions:
        lot = data["lot"]
        plan = stock_services.fefo_plan(lot.article, order.site, totals[lot.article_id])
        expected = [line.lot for line in plan.lines]
        if lot in expected:
            continue
        justification = (data.get("justification") or "").strip()
        if not justification:
            proposed = ", ".join(sorted({item.number for item in expected})) or "aucun"
            errors.append(
                f"Lot {lot.number} ({lot.article.code}) hors FEFO : le système propose {proposed}. "
                "Justifie ce choix."
            )
        else:
            data["reason"] = f"Hors FEFO : {justification}"
            deviations.append(
                {
                    "article_code": lot.article.code,
                    "lot_number": lot.number,
                    "proposed": sorted({item.number for item in expected}),
                    "justification": justification,
                }
            )
    if errors:
        raise ValidationError({"consumptions": errors})

    lot = services.record_production(
        article=order.article,
        quantity=quantity,
        location=order.output_location,
        consumptions=consumptions,
        production_date=production_date,
        user=user,
    )
    return ProductionDeclaration.objects.create(
        order=order,
        lot=lot,
        user=_user(user),
        comment=comment.strip(),
        fefo_deviations=deviations,
        run_start=run_start,
        run_end=run_end,
        scrap_quantity=scrap_quantity or ZERO,
        scrap_reason=(scrap_reason or "").strip(),
    )


# --- Rendement et clôture ----------------------------------------------------------


def produced_quantity(order: ProductionOrder) -> Decimal:
    total = order.declarations.aggregate(total=Sum("lot__initial_quantity"))["total"]
    return total or ZERO


def yield_report(order: ProductionOrder) -> dict:
    """Consommation réelle comparée à la théorique, composant par composant.

    Rendement matière = théorique ÷ réel, sur les composants en kg et en litres.
    """
    produced = produced_quantity(order)
    actual_rows = (
        StockMovement.objects.filter(
            movement_type=MovementType.CONSUMPTION, produced_lot__declaration__order=order
        )
        .values("lot__article")
        .annotate(total=Sum("quantity"))
    )
    actual = {row["lot__article"]: -row["total"] for row in actual_rows}
    components = []
    theoretical_mass = actual_mass = ZERO
    for need in theoretical_needs(order.article, produced) if produced else []:
        real = actual.get(need.component.pk, ZERO)
        gap = None
        if need.gross:
            gap = ((real - need.gross) / need.gross * 100).quantize(Decimal("0.1"))
        components.append(
            {
                "component": need.component,
                "unit": need.unit,
                "theoretical": need.gross,
                "actual": real,
                "gap_pct": gap,
            }
        )
        if need.unit in MASS_UNITS:
            theoretical_mass += need.gross
            actual_mass += real
    mass_yield = None
    if actual_mass:
        mass_yield = (theoretical_mass / actual_mass * 100).quantize(Decimal("0.1"))
    return {
        "produced": produced,
        "components": components,
        "mass_yield": mass_yield,
        "below_target": mass_yield is not None and mass_yield < YIELD_TARGET,
    }


@transaction.atomic
def close_order(order: ProductionOrder, *, user=None) -> ProductionOrder:
    """Clôture l'OF ; sous l'objectif de rendement, une alerte est créée."""
    order = _locked(order)
    if order.status != OrderStatus.LAUNCHED:
        raise ValidationError("Seul un OF lancé peut être clôturé.")
    if not order.declarations.exists():
        raise ValidationError("Aucune production déclarée : annule l'OF au lieu de le clôturer.")
    order.status = OrderStatus.DONE
    order.closed_at = timezone.now()
    order.closed_by = _user(user)
    order.save()

    report = yield_report(order)
    if report["below_target"]:
        raise_alert(
            AlertType.LOW_YIELD,
            AlertLevel.WARNING,
            f"Rendement matière de {report['mass_yield']} % sur l'OF {order.number} "
            f"({order.article.code}), sous l'objectif de {YIELD_TARGET:.0f} %.",
            location=order.output_location,
            allow_duplicate=True,
        )
    return order
