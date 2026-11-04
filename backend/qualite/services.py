"""Traçabilité (règle 1), rappel produit (règle 9) et allergènes (règle 8)."""

import csv
import io
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max, Sum
from django.utils import timezone

from referentiel.choices import ArticleType
from referentiel.models import Allergen, Article, CustomerWarehouse, Location
from referentiel.services import next_document_number
from stocks import services as stock_services
from stocks.choices import LotStatus, MovementType
from stocks.models import Lot, StockMovement

from .models import ProductRecall

# Sécurité contre une boucle de données : une nomenclature ne dépasse jamais cette profondeur
MAX_DEPTH = 15


# --- Traçabilité amont et aval ---------------------------------------------------


@dataclass
class TraceNode:
    lot: Lot
    quantity: Decimal | None = None  # quantité de ce lot consommée par le parent / dans l'enfant
    children: list[TraceNode] = field(default_factory=list)
    shipments: list[dict] = field(default_factory=list)


def _consumption_rows(**filters):
    return (
        StockMovement.objects.filter(movement_type=MovementType.CONSUMPTION, **filters)
        .values("lot", "produced_lot")
        .annotate(quantity=Sum("quantity"))
        .order_by("lot", "produced_lot")
    )


def upstream(lot: Lot, _depth: int = 0, _path: frozenset = frozenset()) -> TraceNode:
    """Tout ce qui a servi à fabriquer ce lot : matières, semi-finis, emballages, à tous niveaux."""
    node = TraceNode(lot=lot)
    if _depth >= MAX_DEPTH:
        return node
    rows = list(_consumption_rows(produced_lot=lot))
    lots = Lot.objects.select_related("article").in_bulk({row["lot"] for row in rows})
    for row in rows:
        if row["lot"] in _path:
            continue
        child = upstream(lots[row["lot"]], _depth + 1, _path | {lot.pk})
        child.quantity = -row["quantity"]
        node.children.append(child)
    return node


def downstream(lot: Lot, _depth: int = 0, _path: frozenset = frozenset()) -> TraceNode:
    """Tout ce qui a été fabriqué avec ce lot, à tous les niveaux, et les livraisons clients."""
    node = TraceNode(lot=lot, shipments=shipments_of([lot.pk]).get(lot.pk, []))
    if _depth >= MAX_DEPTH:
        return node
    rows = list(_consumption_rows(lot=lot))
    lots = Lot.objects.select_related("article").in_bulk({row["produced_lot"] for row in rows})
    for row in rows:
        if row["produced_lot"] in _path:
            continue
        child = downstream(lots[row["produced_lot"]], _depth + 1, _path | {lot.pk})
        child.quantity = -row["quantity"]
        node.children.append(child)
    return node


def shipments_of(lot_ids) -> dict[int, list[dict]]:
    """Livraisons par lot : enseigne, entrepôt, quantité totale, dernière date."""
    rows = (
        StockMovement.objects.filter(movement_type=MovementType.SHIPMENT, lot__in=lot_ids)
        .values("lot", "customer_warehouse")
        .annotate(quantity=Sum("quantity"), last_shipped=Max("created_at"))
        .order_by("lot", "customer_warehouse")
    )
    warehouses = CustomerWarehouse.objects.select_related("customer").in_bulk(
        {row["customer_warehouse"] for row in rows}
    )
    result: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        warehouse = warehouses[row["customer_warehouse"]]
        result[row["lot"]].append(
            {
                "warehouse": warehouse,
                "quantity": -row["quantity"],
                "last_shipped": row["last_shipped"],
            }
        )
    return result


# --- Rappel produit -----------------------------------------------------------


@dataclass
class ImpactedLot:
    lot: Lot
    level: int  # 0 = lot d'origine, 1 = fabriqué avec lui, 2 = niveau suivant…
    stock: list[tuple[Location, Decimal]]

    @property
    def stock_total(self) -> Decimal:
        return sum((quantity for _, quantity in self.stock), Decimal("0"))


@dataclass
class RecallImpact:
    origin: Lot
    lots: list[ImpactedLot]
    deliveries: list[dict]
    computed_at: datetime

    @property
    def lots_to_block(self) -> list[Lot]:
        return [
            item.lot
            for item in self.lots
            if item.stock_total > 0
            and item.lot.status in (LotStatus.RELEASED, LotStatus.QUARANTINE)
        ]


def recall_impact(lot: Lot) -> RecallImpact:
    """Règle 9 : tous les lots liés, leurs stocks restants et les clients livrés.

    Parcours de l'aval niveau par niveau, en quelques requêtes groupées (rapide même
    avec beaucoup de lots).
    """
    levels = {lot.pk: 0}
    frontier = {lot.pk}
    depth = 0
    while frontier and depth < MAX_DEPTH:
        depth += 1
        produced = set(
            StockMovement.objects.filter(movement_type=MovementType.CONSUMPTION, lot__in=frontier)
            .values_list("produced_lot", flat=True)
            .distinct()
        )
        frontier = produced - levels.keys()
        for lot_id in frontier:
            levels[lot_id] = depth

    lots = Lot.objects.select_related("article").in_bulk(levels.keys())
    stock_rows = (
        StockMovement.objects.filter(lot__in=levels.keys())
        .values("lot", "location")
        .annotate(total=Sum("quantity"))
        .filter(total__gt=0)
    )
    locations = Location.objects.select_related("site").in_bulk(
        {row["location"] for row in stock_rows}
    )
    stock: dict[int, list] = defaultdict(list)
    for row in stock_rows:
        stock[row["lot"]].append((locations[row["location"]], row["total"]))

    impacted = sorted(
        (
            ImpactedLot(lot=lots[lot_id], level=level, stock=stock[lot_id])
            for lot_id, level in levels.items()
        ),
        key=lambda item: (item.level, item.lot.article.code, item.lot.number),
    )
    deliveries = []
    for lot_id, rows in shipments_of(levels.keys()).items():
        for row in rows:
            deliveries.append({"lot": lots[lot_id], **row})
    deliveries.sort(
        key=lambda d: (d["warehouse"].customer.code, d["warehouse"].code, d["lot"].number)
    )
    return RecallImpact(
        origin=lot, lots=impacted, deliveries=deliveries, computed_at=timezone.now()
    )


def impact_to_dict(impact: RecallImpact) -> dict:
    """Version texte (JSON) du résultat, pour l'API et la photo du rappel."""

    def lot_info(lot: Lot) -> dict:
        return {
            "id": lot.id,
            "number": lot.number,
            "article_code": lot.article.code,
            "article_name": lot.article.name,
            "article_type": lot.article.article_type,
            "unit": lot.article.unit,
            "status": lot.status,
            "status_label": lot.get_status_display(),
            "expiry_date": lot.expiry_date.isoformat() if lot.expiry_date else None,
        }

    customers: dict[str, dict] = {}
    for delivery in impact.deliveries:
        customer = delivery["warehouse"].customer
        entry = customers.setdefault(
            customer.code,
            {"code": customer.code, "name": customer.name, "deliveries": 0, "quantities": {}},
        )
        entry["deliveries"] += 1
        unit = delivery["lot"].article.unit
        entry["quantities"][unit] = str(
            Decimal(entry["quantities"].get(unit, "0")) + delivery["quantity"]
        )

    return {
        "origin": lot_info(impact.origin),
        "computed_at": impact.computed_at.isoformat(),
        "lots": [
            {
                **lot_info(item.lot),
                "level": item.level,
                "stock_total": str(item.stock_total),
                "stock": [
                    {
                        "location_code": location.code,
                        "site_code": location.site.code,
                        "quantity": str(quantity),
                    }
                    for location, quantity in item.stock
                ],
            }
            for item in impact.lots
        ],
        "deliveries": [
            {
                "lot_number": d["lot"].number,
                "article_code": d["lot"].article.code,
                "article_name": d["lot"].article.name,
                "unit": d["lot"].article.unit,
                "expiry_date": d["lot"].expiry_date.isoformat() if d["lot"].expiry_date else None,
                "customer_code": d["warehouse"].customer.code,
                "customer_name": d["warehouse"].customer.name,
                "warehouse_code": d["warehouse"].code,
                "warehouse_name": d["warehouse"].name,
                "city": d["warehouse"].city,
                "quantity": str(d["quantity"]),
                "last_shipped": d["last_shipped"].isoformat(),
            }
            for d in impact.deliveries
        ],
        "customers": sorted(customers.values(), key=lambda c: c["code"]),
        "lots_to_block": [lot.number for lot in impact.lots_to_block],
    }


@transaction.atomic
def launch_recall(lot: Lot, *, reason: str, user=None) -> ProductRecall:
    """Lance officiellement un rappel : photo de l'impact et blocage des lots ayant du stock."""
    reason = reason.strip()
    if not reason:
        raise ValidationError({"reason": "Indique le motif du rappel."})
    impact = recall_impact(lot)
    number = next_document_number(f"RAP-{timezone.localdate().year}", 5)
    blocked = [
        stock_services.block_lot(item, user=user, reason=f"Rappel {number} : {reason}")
        for item in impact.lots_to_block
    ]
    snapshot = impact_to_dict(impact)
    snapshot["blocked_lots"] = [item.number for item in blocked]
    recall = ProductRecall.objects.create(
        number=number,
        origin_lot=lot,
        reason=reason,
        created_by=user if user is not None and user.is_authenticated else None,
        snapshot=snapshot,
    )
    recall.blocked_lots.set(blocked)
    return recall


CSV_COLUMNS = [
    ("customer_code", "Code enseigne"),
    ("customer_name", "Enseigne"),
    ("warehouse_code", "Code entrepôt"),
    ("warehouse_name", "Entrepôt"),
    ("city", "Ville"),
    ("lot_number", "Lot"),
    ("article_code", "Article"),
    ("article_name", "Désignation"),
    ("expiry_date", "DLC / DDM"),
    ("quantity", "Quantité livrée"),
    ("unit", "Unité"),
    ("last_shipped", "Dernière livraison"),
]


def recall_csv(recall: ProductRecall) -> str:
    """Liste des clients à prévenir, au format CSV lisible par Excel (séparateur « ; »)."""
    buffer = io.StringIO()
    buffer.write("﻿")  # indique à Excel que le fichier est en UTF-8 (accents)
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow([label for _, label in CSV_COLUMNS])
    for delivery in recall.snapshot.get("deliveries", []):
        row = []
        for key, _ in CSV_COLUMNS:
            value = delivery.get(key) or ""
            if key == "quantity":
                value = value.replace(".", ",")
            elif key in ("expiry_date", "last_shipped") and value:
                value = datetime.fromisoformat(value).strftime("%d/%m/%Y")
            row.append(value)
        writer.writerow(row)
    return buffer.getvalue()


# --- Allergènes (règle 8) ------------------------------------------------------


def compute_allergens(article: Article) -> list[dict]:
    """Allergènes d'un article, calculés à partir de sa nomenclature à tous les niveaux.

    Renvoie, pour chaque allergène, les chemins qui l'apportent
    (ex. Lait : SF-BECHAMEL → MP-LAI-CREME35).
    """
    sources: dict[int, list[list[str]]] = defaultdict(list)

    def walk(current: Article, path: list[str], seen: frozenset) -> None:
        if current.article_type == ArticleType.RAW_MATERIAL:
            for allergen in current.allergens.all():
                sources[allergen.pk].append([*path, current.code])
            return
        if len(path) >= MAX_DEPTH or not hasattr(current, "bom"):
            return
        for line in current.bom.lines.select_related("component"):
            component = line.component
            if component.pk not in seen:
                walk(component, [*path, current.code], seen | {component.pk})

    walk(article, [], frozenset({article.pk}))
    allergens = Allergen.objects.in_bulk(sources.keys())
    return [
        {
            "allergen": allergens[allergen_id],
            # Le premier élément du chemin est l'article lui-même : on ne le répète pas
            "sources": [path[1:] if len(path) > 1 else path for path in sources[allergen_id]],
        }
        for allergen_id in sorted(sources, key=lambda pk: allergens[pk].order)
    ]
