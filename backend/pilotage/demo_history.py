"""Historique de démonstration : six semaines d'activité rejouées jour par jour (phase 8).

Sans historique, les indicateurs de pilotage n'ont presque rien à mesurer. Ce module rejoue
chaque journée passée comme si l'ERP avait tourné : réceptions de matières, fabrications
(semi-finis puis produits finis), libérations qualité, commandes des enseignes, préparation
FEFO et expédition, sorties d'invendables.

Tout passe par les fonctions métier habituelles : les règles (FEFO, DLC minimale client,
statuts de lot, mouvements, numérotation…) s'appliquent exactement comme en temps réel.
Pour que chaque enregistrement porte la date de sa journée, l'horloge de Django est
« avancée » jour après jour pendant le chargement (`simulated_clock`).

Quelques incidents volontaires rendent les indicateurs réalistes : une panne de ligne
(ruptures), un transporteur en retard (livraisons hors délai), une fuite en cuisson
(rendement faible), des réceptions non conformes, des invendables.

TRS (phase 10) : chaque OF de produit fini a sa plage de marche sur la ligne (à partir de 5 h,
les OF de la journée à la suite), avec des changements de série, des micro-arrêts, quelques
pannes et manques matière, une cadence réelle un peu sous la cadence nominale et 0,3 à 2 % de
rebuts. La panne de ligne arrête la production après une demi-heure.

Calendrier (phase 11b) : l'historique suit le vrai calendrier. Les enseignes commandent du
lundi au samedi (heure limite de 11 h, jours fériés exclus) pour le prochain jour de livraison ;
la plateforme expédie le jour même. Les usines produisent du lundi au vendredi : chaque
fabrication couvre les expéditions jusqu'au jour de production suivant (samedi compris). La
qualité libère à 14 h la production du matin. Un produit dont la DLC restante serait trop
courte à la livraison (produits à 8 jours livrés le lundi) n'est pas commandé ce jour-là.

Prévisions (phase 9a) : la prévision est figée chaque lundi à 5 h, dès qu'il existe des
commandes passées, pour mesurer la fiabilité à S-1. Une promotion annoncée 7 semaines
avant double les commandes d'une enseigne pendant une semaine (production comprise).
"""

import random
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from decimal import ROUND_CEILING, Decimal
from unittest import mock

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from achats import services as purchasing
from achats.models import SupplierPrice
from previsions import forecast
from previsions.models import Promotion
from production import oee
from production import orders as production
from production.models import StopCategory
from referentiel import calendar
from referentiel.calendar import Activity
from referentiel.choices import ArticleType, DateType, TemperatureClass
from referentiel.models import (
    Article,
    Customer,
    Location,
    ProductionLine,
    Site,
    Supplier,
    SupplierArticle,
)
from referentiel.services import line_accepts
from stocks import services as stock_services
from stocks.choices import LotStatus, UnsoldDestination
from stocks.models import Lot
from ventes import orders as sales
from ventes import shipping
from ventes.models import CustomerOrder, CustomerOrderLine, OrderSource, OrderStatus

# Six semaines : il faut quelques semaines de commandes avant que les prévisions figées
# puissent être comparées aux commandes réelles (fiabilité à S-1 sur trois semaines)
HISTORY_DAYS = 42
# Les commandes des enseignes commencent après deux jours de production
FIRST_ORDER_DAY = 2
REFERENCE = "HIST"
SEED = 2026
QUALITY_REASON = "Contrôle qualité conforme"
ZERO = Decimal("0")
UNLIMITED = Decimal("1000000000")

# Produits finis de l'historique : demande moyenne par enseigne et par jour (unités)
DAILY_DEMAND = {
    "PF-PAT-LASBOL-BRE-300": 360,
    "PF-PAT-LASBOL-ENS1-300": 480,
    "PF-GRA-GRADAU-BRE-1000": 120,
    "PF-GRA-HACHIS-BRE-300": 240,
    "PF-GRA-HACHIS-ENS5-300": 480,
    "PF-SAU-BOEBOU-BRE-300": 180,
    "PF-SAL-PIEMON-BRE-300": 180,
    "PF-SAL-PIEMON-ENS6-300": 240,
    "PF-TAB-TABOR-BRE-500": 240,
    "PF-ENT-CARAP-BRE-250": 240,
    "PF-ENT-CELREM-ENS2-250": 360,
}
# Variation de la demande d'une enseigne d'un jour à l'autre (± 15 %)
DEMAND_SPREAD = 0.15
# Stock de sécurité visé (en jours de demande) : faible pour les produits à DLC courte,
# qu'il faut expédier dès le lendemain de leur fabrication
SAFETY_DAYS_SHORT = Decimal("0.03")
SAFETY_DAYS_LONG = Decimal("1")
SHORT_SHELF_LIFE_DAYS = 10
# Marge prise sur les matières pour absorber les écarts de consommation
MATERIAL_MARGIN = Decimal("1.08")
# Achats, en jours de besoin : frais selon sa durée de vie (au plus la moitié, 4 jours
# maximum, la production s'arrêtant le week-end), sec, surgelés et emballages : 24 jours
FRESH_MAX_COVER_DAYS = 4
OTHER_COVER_DAYS = 24
# Navette entrepôt → usine : jusqu'à 3 jours de besoin d'un coup
FACTORY_SUPPLY_DAYS = 3
NON_COMPLIANT_RATE = 0.02

# Incidents volontaires : (jour de l'historique, …)
BREAKDOWN = (9, "PF-SAU-BOEBOU-BRE-300", "Panne de la ligne : production arrêtée après 30 min")
# TRS (phase 10) : première équipe à 5 h ; la panne laisse 20 % de l'OF fabriqué
SHIFT_START_HOUR = 5
BREAKDOWN_SHARE = Decimal("0.2")
BREAKDOWN_MINUTES = 300
# Incidents datés : le premier jour ouvré concerné à partir du jour indiqué
LATE_CARRIER = (16, "ENS3", "Translog Froid Ouest")
RELEASE_HOUR = 14  # libération qualité de la production du matin (phase 11b)
LEAK = (22, "PF-GRA-GRADAU-BRE-1000", Decimal("1.075"), "Fuite sur la cuve de cuisson")
# Promotion réalisée : (enseigne, produit, semaines avant la semaine courante, coefficient)
PAST_PROMOTION = ("ENS2", "PF-PAT-LASBOL-BRE-300", 2, Decimal("2"))
PROMOTION_NOTICE_DAYS = 49
FORECAST_HOUR = 5

STORAGE = {
    TemperatureClass.CHILLED: "MPE-FP-01",
    TemperatureClass.FROZEN: "MPE-FN-01",
    TemperatureClass.AMBIENT: "MPE-AMB-01",
}
QUARANTINE = {
    TemperatureClass.CHILLED: "MPE-QUAR",
    TemperatureClass.FROZEN: "MPE-QUAR-FN",
    TemperatureClass.AMBIENT: "MPE-QUAR-AMB",
}


@contextmanager
def simulated_clock(moment: datetime):
    """Fait croire à Django qu'on est à `moment` (dates de création, « aujourd'hui »…)."""
    with mock.patch("django.utils.timezone.now", return_value=moment):
        yield


def _at(day: date, hour: int, minute: int = 0) -> datetime:
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


def _round_up(value: Decimal, step: Decimal) -> Decimal:
    return (value / step).to_integral_value(rounding=ROUND_CEILING) * step


def _days(value: Decimal) -> int:
    return int(value.to_integral_value(rounding=ROUND_CEILING))


class History:
    """Rejoue les journées de l'historique, de la plus ancienne à hier."""

    def __init__(self, days: int):
        self.days = days
        self.today = timezone.localdate()
        self.start = self.today - timedelta(days=days)
        self.rng = random.Random(SEED)
        self.loc = {location.code: location for location in Location.objects.all()}
        self.warehouse = Site.objects.get(code="MPE")
        self.products = {
            article.code: article
            for article in Article.objects.filter(code__in=DAILY_DEMAND).select_related(
                "recipe__family__site"
            )
        }
        self.lines = {}
        for article in self.products.values():
            for line in ProductionLine.objects.filter(active=True).order_by("code"):
                if line_accepts(line, article) is None:
                    self.lines[article.code] = line
                    break
        # Enseignes qui achètent chaque produit, avec leur demande moyenne
        self.buyers: dict[str, list[Customer]] = {code: [] for code in self.products}
        self.customers = list(Customer.objects.filter(active=True).order_by("code"))
        for customer in self.customers:
            for code, article in self.products.items():
                if sales.orderable_refusal(customer, article) is None:
                    self.buyers[code].append(customer)
        self.delayed: list[CustomerOrder] = []
        # TRS : heure de disponibilité de chaque ligne dans la journée ; tirages séparés pour ne
        # pas changer les autres données de l'historique
        self.line_clock: dict[tuple[int, date], datetime] = {}
        # Calendrier : réponses mises en cache (le calendrier lit les fermetures en base)
        self.open_cache: dict[tuple, bool] = {}
        self.delivery_cache: dict[date, date] = {}
        self.incidents_done: set[str] = set()
        self.oee_rng = random.Random(SEED + 10)
        self.counts = {"commandes fournisseurs": 0, "OF": 0, "commandes clients": 0}
        self.counts["seconds fournisseurs référencés"] = self._second_sources()
        self.promotions = self._past_promotion()

    def _second_sources(self) -> int:
        """Une matière dont le seul fournisseur n'est pas audité ne peut pas être commandée :
        on la référence aussi chez un fournisseur audité de la même catégorie, au même prix."""
        created = 0
        materials = Article.objects.filter(article_type=ArticleType.RAW_MATERIAL, active=True)
        for article in materials.exclude(supplier_links__supplier__audited=True):
            supplier = (
                Supplier.objects.filter(audited=True, active=True, categories=article.category)
                .order_by("code")
                .first()
            )
            current = article.supplier_links.first()
            if supplier is None or current is None:
                continue
            link = SupplierArticle.objects.create(supplier=supplier, article=article)
            for price in current.prices.all():
                SupplierPrice.objects.create(
                    supplier_article=link,
                    unit_price=price.unit_price,
                    valid_from=price.valid_from,
                    valid_to=price.valid_to,
                )
            created += 1
        return created

    # --- Prévisions et promotions (phase 9a) --------------------------------------------

    def _past_promotion(self) -> list[Promotion]:
        """Promotion déjà réalisée, saisie le jour de son annonce (7 semaines avant)."""
        customer_code, code, weeks_ago, coefficient = PAST_PROMOTION
        customer = next((c for c in self.customers if c.code == customer_code), None)
        week = forecast.current_week() - timedelta(days=7 * weeks_ago)
        if customer is None or code not in self.products or week < self.start:
            return []  # historique trop court (tests)
        announced = week - timedelta(days=PROMOTION_NOTICE_DAYS)
        promotion = Promotion.objects.create(
            customer=customer,
            article=self.products[code],
            first_week=week,
            last_week=week,
            coefficient=coefficient,
            announced_on=announced,
            created_at=_at(announced, 10),
            comment="Historique de démonstration",
        )
        self.counts["promotions réalisées"] = 1
        return [promotion]

    # --- Calendrier (phase 11b) ------------------------------------------------------------

    def _open(self, day: date, activity: Activity, site_code: str | None = None) -> bool:
        key = (day, activity, site_code)
        if key not in self.open_cache:
            self.open_cache[key] = calendar.is_open(day, activity, site_code)
        return self.open_cache[key]

    def _delivery(self, day: date) -> date:
        """Jour de livraison d'une commande reçue ce jour-là à 9 h 30."""
        if day not in self.delivery_cache:
            self.delivery_cache[day] = sales.earliest_delivery_date(_at(day, 9, 30))
        return self.delivery_cache[day]

    def _site(self, article: Article) -> str:
        return self.lines[article.code].site.code

    def _next_production_day(self, article: Article, day: date) -> date:
        current = day + timedelta(days=1)
        while not self._open(current, Activity.PRODUCTION, self._site(article)):
            current += timedelta(days=1)
        return current

    def _last_production_day(self, article: Article, day: date) -> date:
        current = day
        while not self._open(current, Activity.PRODUCTION, self._site(article)):
            current -= timedelta(days=1)
        return current

    def _orderable(self, customer: Customer, article: Article, day: date) -> bool:
        """L'enseigne ne commande pas un produit qui arriverait avec une DLC trop courte :
        fabriqué au plus tard le dernier jour de production avant l'expédition, il doit garder
        la part minimale de sa durée de vie à la livraison (ex. produit à 8 jours fabriqué le
        vendredi et livré le lundi)."""
        made = self._last_production_day(article, day)
        delivery = self._delivery(day)
        needed = _days(
            Decimal(article.shelf_life_days) * customer.min_remaining_shelf_life_pct / 100
        )
        return (delivery - made).days + needed <= article.shelf_life_days

    def _coefficient(self, customer: Customer, article: Article, delivery: date) -> Decimal:
        for promotion in self.promotions:
            if (
                promotion.customer_id == customer.pk
                and promotion.article_id == article.pk
                and promotion.first_week <= delivery < promotion.last_week + timedelta(days=7)
            ):
                return promotion.coefficient
        return Decimal("1")

    def _demand(self, article: Article, day: date) -> Decimal:
        """Demande moyenne des commandes reçues (et expédiées) ce jour-là ; aucune le dimanche,
        les jours fériés, ni avant le début des commandes."""
        if day < self.start + timedelta(days=FIRST_ORDER_DAY) or not self._open(
            day, Activity.SHIPPING
        ):
            return ZERO
        delivery = self._delivery(day)
        return sum(
            (
                DAILY_DEMAND[article.code] * self._coefficient(customer, article, delivery)
                for customer in self.buyers[article.code]
                if self._orderable(customer, article, day)
            ),
            ZERO,
        )

    def _freeze_forecast(self, day: date) -> None:
        """Version du lundi 5 h, dès qu'une semaine complète de commandes est passée : une
        première semaine partielle donnerait une prévision bien trop basse."""
        if day - timedelta(days=7) < self.start + timedelta(days=FIRST_ORDER_DAY):
            return
        past_orders = CustomerOrderLine.objects.filter(
            order__requested_delivery_date__lt=day
        ).exclude(order__status="annulee")
        if past_orders.exists() and forecast.freeze_weekly() is not None:
            self.counts["prévisions figées"] = self.counts.get("prévisions figées", 0) + 1

    # --- Journée type ---------------------------------------------------------------

    def run(self) -> dict:
        for offset in range(self.days):
            day = self.start + timedelta(days=offset)
            if day.weekday() == 0:
                with simulated_clock(_at(day, FORECAST_HOUR)):
                    self._freeze_forecast(day)
            shipping_day = self._open(day, Activity.SHIPPING)
            if shipping_day:
                with simulated_clock(_at(day, 7)):
                    self._ship_delayed(day)
            if offset >= FIRST_ORDER_DAY - 1:
                with simulated_clock(_at(day, 8)):
                    self._produce(offset, day)
            with simulated_clock(_at(day, RELEASE_HOUR)):
                self._release_finished_products(day)
            if offset >= FIRST_ORDER_DAY and shipping_day:
                with simulated_clock(_at(day, 9, 30)):
                    received = self._receive_customer_orders(day)
                with simulated_clock(_at(day, 15)):
                    self._ship(offset, received)
                    self._ship_pending(day)
            with simulated_clock(_at(day, 19)):
                self._dispose_unsellable(day)
                self._destroy_expired_materials(day)
        return self.counts

    # --- Achats et approvisionnement des usines -------------------------------------------

    def _supplier_link(self, article: Article) -> SupplierArticle:
        links = SupplierArticle.objects.filter(
            article=article, supplier__audited=True, supplier__active=True
        ).select_related("supplier")
        return links.filter(is_main_supplier=True).first() or links.first()

    def _purchase(self, article: Article, quantity: Decimal, day: date, compliant: bool) -> Lot:
        """Commande, réception (contrôles), libération qualité et rangement d'une matière."""
        link = self._supplier_link(article)
        quantity = max(quantity, link.min_order_quantity or ZERO)
        step = Decimal("1000") if article.article_type == ArticleType.PACKAGING else Decimal("10")
        quantity = _round_up(quantity, step)
        supplier = link.supplier
        order = purchasing.create_purchase_order(
            supplier=supplier,
            delivery_site=self.warehouse,
            order_date=day - timedelta(days=supplier.lead_time_days),
            lines=[{"article": article, "quantity": quantity}],
            comment=f"{REFERENCE} – réapprovisionnement",
        )
        purchasing.send_order(order)
        self.counts["commandes fournisseurs"] += 1

        temperature_class = article.storage_temperature_class
        temperature = None
        if temperature_class == TemperatureClass.CHILLED:
            temperature = Decimal(self.rng.choice(["2.3", "2.8", "3.1", "3.5", "3.8"]))
            if not compliant:
                temperature = Decimal("6.2")
        elif temperature_class == TemperatureClass.FROZEN:
            temperature = Decimal("-19.5")
        expiry = None
        if article.date_type != DateType.NONE and article.shelf_life_days:
            expiry = day + timedelta(days=round(article.shelf_life_days * 0.9))
        line = order.lines.get()
        reception = purchasing.create_reception(
            order=order,
            location=self.loc[QUARANTINE[temperature_class]],
            delivery_note_number=f"BL-{supplier.code[-3:]}-{day:%m%d}-{order.pk}",
            received_at=_at(day, 6),
            lines=[
                {
                    "order_line": line,
                    "quantity": quantity,
                    "supplier_lot_number": f"{supplier.code[-3:]}-{day:%y%m%d}-{order.pk}",
                    "expiry_date": expiry,
                    "temperature": temperature,
                    # Une matière ambiante non conforme : emballage abîmé
                    "appearance_ok": compliant or temperature is not None,
                }
            ],
        )
        lot = reception.lines.get().lot
        if lot.status != LotStatus.QUARANTINE:
            # Non conforme : le lot reste bloqué (retour fournisseur), on recommande
            return self._purchase(article, quantity, day, compliant=True)
        stock_services.release_lot(lot, reason=QUALITY_REASON)
        storage = STORAGE[temperature_class]
        if article.article_type == ArticleType.PACKAGING:
            storage = "MPE-EMB-01"
        stock_services.transfer(
            lot,
            from_location=self.loc[QUARANTINE[temperature_class]],
            to_location=self.loc[storage],
            quantity=quantity,
            reason="Rangement après libération",
        )
        return lot

    @staticmethod
    def _available(article: Article, site: Site) -> Decimal:
        plan = stock_services.fefo_plan(article, site, UNLIMITED)
        return sum((line.available for line in plan.lines), ZERO)

    def _supply(self, article: Article, site: Site, quantity: Decimal, day: date) -> None:
        """Amène à l'usine la quantité manquante (lots FEFO de l'entrepôt, achat si besoin)."""
        missing = quantity - self._available(article, site)
        if missing <= 0:
            return
        # `missing` vaut environ un jour de besoin : on achète et on amène plusieurs jours
        cover_days = OTHER_COVER_DAYS
        if article.storage_temperature_class == TemperatureClass.CHILLED:
            cover_days = max(1, min(FRESH_MAX_COVER_DAYS, (article.shelf_life_days or 2) // 2))
        wanted = missing * min(FACTORY_SUPPLY_DAYS, cover_days)
        in_warehouse = self._available(article, self.warehouse)
        if in_warehouse < missing:
            compliant = self.rng.random() >= NON_COMPLIANT_RATE
            self._purchase(article, missing * cover_days, day, compliant)
            in_warehouse = self._available(article, self.warehouse)
        chilled = article.storage_temperature_class == TemperatureClass.CHILLED
        target = self.loc[f"{site.code}-{'CF' if chilled else 'AMB'}-MP"]
        quantity = min(wanted, in_warehouse)
        for line in stock_services.fefo_plan(article, self.warehouse, quantity).lines:
            stock_services.transfer(
                line.lot,
                from_location=line.location,
                to_location=target,
                quantity=line.take,
                reason="Approvisionnement usine",
            )

    # --- Production -----------------------------------------------------------------

    def _usable_stock(self, article: Article, day: date) -> Decimal:
        """Stock de produit fini encore assez frais pour être expédié ce jour-là."""
        min_expiry = day + timedelta(days=1 + _days(Decimal(article.shelf_life_days) * 75 / 100))
        lots = Lot.objects.filter(
            article=article,
            status__in=[LotStatus.RELEASED, LotStatus.QUARANTINE],
            expiry_date__gte=min_expiry,
            created_at__lte=timezone.now(),
        )
        return sum((lot.quantity for lot in lots), ZERO)

    def _planned_quantity(self, article: Article, day: date, first: bool = False) -> Decimal:
        """Libérée à 14 h, la fabrication du jour part dans les expéditions de 15 h et couvre
        celles des jours suivants jusqu'au prochain jour de production (le samedi pour une
        fabrication du vendredi), plus le stock de sécurité, moins le stock utilisable."""
        mean = Decimal(DAILY_DEMAND[article.code] * len(self.buyers[article.code]))
        short = article.shelf_life_days <= SHORT_SHELF_LIFE_DAYS
        safety = SAFETY_DAYS_SHORT if short else SAFETY_DAYS_LONG
        covered = ZERO
        current, next_day = day, self._next_production_day(article, day)
        if (next_day - day).days > 1:
            # Veille de week-end ou de jour férié : pas de stock de sécurité, il vieillirait
            # pendant la fermeture et ne passerait plus la DLC minimale des enseignes
            safety = SAFETY_DAYS_SHORT
        while current < next_day:
            covered += self._demand(article, current) + self._pending_demand(article, current)
            current += timedelta(days=1)
        quantity = covered + mean * safety - self._usable_stock(article, day)
        return _round_up(quantity, Decimal("12")) if quantity > 0 else ZERO

    def _run(self, order, quantity: Decimal, day: date, breakdown: bool) -> dict:
        """Plage de marche de l'OF sur sa ligne, arrêts compris, et rebuts (TRS)."""
        line = order.line
        key = (line.pk, day)
        rng = self.oee_rng
        start = self.line_clock.get(key, _at(day, SHIFT_START_HOUR))
        cursor = start
        stops = []

        def stop(category, minutes):
            nonlocal cursor
            stops.append((cursor, cursor + timedelta(minutes=minutes), category))
            cursor += timedelta(minutes=minutes)

        if key in self.line_clock:
            stop(StopCategory.CHANGEOVER, rng.randint(3, 7))
        speed = Decimal(str(round(rng.uniform(0.85, 0.97), 3)))
        minutes = float(quantity / (line.capacity_per_hour * speed) * 60)
        if breakdown:
            cursor += timedelta(minutes=30)
            stop(StopCategory.BREAKDOWN, BREAKDOWN_MINUTES)
            minutes = max(0.0, minutes - 30)
        elif rng.random() < 0.08:
            first = rng.uniform(0.2, 0.8) * minutes
            cursor += timedelta(minutes=first)
            stop(StopCategory.BREAKDOWN, rng.randint(20, 75))
            minutes -= first
        if rng.random() < 0.25:
            stop(StopCategory.ADJUSTMENT, rng.randint(3, 8))
        if rng.random() < 0.03:
            stop(StopCategory.MATERIAL_SHORTAGE, rng.randint(15, 40))
        cursor += timedelta(minutes=minutes)
        end = cursor.replace(second=0, microsecond=0) + timedelta(minutes=1)
        self.line_clock[key] = end
        scrap = (quantity * Decimal(str(round(rng.uniform(0.003, 0.02), 4)))).to_integral_value()
        reason = "Barquettes mal operculées" if scrap else ""
        return {"run_start": start, "run_end": end, "scrap": scrap, "reason": reason,
                "stops": stops}  # fmt: skip

    def _declare(self, order, quantity: Decimal, factor: Decimal, run=None) -> None:
        """Déclaration avec les lots proposés par le FEFO ; `factor` simule les écarts matière."""
        consumptions = []
        for row in production.proposal(order, quantity):
            need = row["need"]
            ratio = factor if need.unit in production.MASS_UNITS else Decimal("1")
            remaining = (need.gross * ratio).quantize(Decimal("0.001"))
            for item in row["lots"]:
                take = min(item["available"], remaining)
                if take > 0:
                    consumptions.append(
                        {"lot": item["lot"], "location": item["location"], "quantity": take}
                    )
                    remaining -= take
        if run is None:
            production.declare_production(order, quantity=quantity, consumptions=consumptions)
            return
        # La saisie se fait après la marche : l'horloge simulée avance jusqu'à sa fin
        with simulated_clock(max(timezone.now(), run["run_end"] + timedelta(minutes=1))):
            production.declare_production(
                order, quantity=quantity, consumptions=consumptions, run_start=run["run_start"],
                run_end=run["run_end"], scrap_quantity=run["scrap"], scrap_reason=run["reason"],
                require_run=True,
            )  # fmt: skip
            for started_at, ended_at, category in run["stops"]:
                oee.record_stop(
                    line=order.line, started_at=started_at, ended_at=ended_at,
                    category=category, production_order=order,
                )  # fmt: skip
        self.counts["arrêts de ligne"] = self.counts.get("arrêts de ligne", 0) + len(run["stops"])

    def _make(
        self, article: Article, quantity: Decimal, day: date, site: Site, factor=None, comment="",
        breakdown: bool = False,
    ):  # fmt: skip
        """Approvisionne, fabrique (OF lancé, déclaré, clôturé) et renvoie le lot fabriqué."""
        factor = factor or Decimal(str(round(self.rng.uniform(0.995, 1.035), 3)))
        for need in production.theoretical_needs(article, quantity):
            gross = need.gross * MATERIAL_MARGIN
            if need.component.article_type == ArticleType.SEMI_FINISHED:
                missing = gross - self._available(need.component, site)
                if missing > 0:
                    lot = self._make(need.component, _round_up(missing, Decimal("10")), day, site)
                    stock_services.release_lot(lot, reason=QUALITY_REASON)
            else:
                self._supply(need.component, site, gross, day)
        finished = article.article_type == ArticleType.FINISHED_PRODUCT
        line = self.lines[article.code] if finished else None
        order = production.create_order(
            article=article,
            planned_quantity=quantity,
            planned_date=day,
            line=line,
            site=None if line else site,
            comment=comment,
        )
        production.launch_order(order)
        run = self._run(order, quantity, day, breakdown) if line else None
        self._declare(order, quantity, factor, run)
        production.close_order(order)
        self.counts["OF"] += 1
        return order.declarations.get().lot

    def _incident(self, name: str, offset: int, start: int) -> bool:
        """Vrai la première fois qu'on atteint le jour de l'incident (jour ouvré suivant si
        le jour prévu ne l'est pas)."""
        if offset < start or name in self.incidents_done:
            return False
        self.incidents_done.add(name)
        return True

    def _produce(self, offset: int, day: date) -> None:
        for code, article in self.products.items():
            if not self._open(day, Activity.PRODUCTION, self._site(article)):
                continue  # usine fermée : week-end, jour férié, fermeture
            quantity = self._planned_quantity(article, day, first=offset < FIRST_ORDER_DAY)
            if quantity <= 0:
                continue
            if code == BREAKDOWN[1] and self._incident("panne", offset, BREAKDOWN[0]):
                # Panne : la ligne s'arrête après 30 min, seule une petite partie est fabriquée
                partial = _round_up(quantity * BREAKDOWN_SHARE, Decimal("12"))
                site = self.lines[code].site
                self._make(article, partial, day, site, comment=BREAKDOWN[2], breakdown=True)
                continue
            factor, comment = None, ""
            if code == LEAK[1] and self._incident("fuite", offset, LEAK[0]):
                factor, comment = LEAK[2], LEAK[3]
            self._make(article, quantity, day, self.lines[code].site, factor, comment)

    def _release_finished_products(self, day: date) -> None:
        """Libération qualité à 14 h des produits finis fabriqués jusqu'au jour même, puis
        rangement en allée A."""
        lots = Lot.objects.filter(
            article__in=self.products.values(),
            status=LotStatus.QUARANTINE,
            production_date__lte=day,
            created_at__lte=timezone.now(),
        )
        for lot in lots:
            stock_services.release_lot(lot, reason=QUALITY_REASON)
            for location, quantity in stock_services.stock_by_location(lot):
                if location.code == "PFN-QUAR":
                    stock_services.transfer(
                        lot,
                        from_location=location,
                        to_location=self.loc["PFN-FRAIS-A"],
                        quantity=quantity,
                        reason="Rangement après libération",
                    )

    # --- Ventes -----------------------------------------------------------------------

    def _receive_customer_orders(self, day: date) -> list[CustomerOrder]:
        received = []
        for customer in self.customers:
            lines = []
            delivery = self._delivery(day)
            for code, buyers in self.buyers.items():
                article = self.products[code]
                if customer in buyers and self._orderable(customer, article, day):
                    spread = self.rng.uniform(1 - DEMAND_SPREAD, 1 + DEMAND_SPREAD)
                    spread *= float(self._coefficient(customer, article, delivery))
                    quantity = max(12, round(DAILY_DEMAND[code] * spread / 12) * 12)
                    lines.append({"article": self.products[code], "quantity": Decimal(quantity)})
            if not lines:
                continue
            warehouses = list(customer.warehouses.filter(active=True).order_by("code"))
            received.append(
                sales.create_order(
                    customer=customer,
                    warehouse=self.rng.choice(warehouses),
                    # Phase 11 : premier jour de livraison possible (heure limite, jours ouvrés)
                    requested_delivery_date=delivery,
                    lines=lines,
                    customer_reference=f"{REFERENCE}-{customer.code}-{day:%Y%m%d}",
                    received_at=timezone.now(),
                    source=OrderSource.EDI,
                    comment="Historique de démonstration",
                )
            )
            self.counts["commandes clients"] += 1
        return received

    def _prepare(self, order: CustomerOrder):
        lines = [
            {
                "order_line": row["order_line"],
                "lot": item.lot,
                "location": item.location,
                "quantity": item.suggested,
            }
            for row in shipping.picking_proposal(order)
            for item in row["lots"]
            if item.suggested > 0
        ]
        if not lines:
            return None  # rupture totale : la commande reste non livrée
        return shipping.prepare_order(order, lines=lines)

    def _ship(self, offset: int, received: list[CustomerOrder]) -> None:
        for order in received:
            if order.customer.code == LATE_CARRIER[1] and self._incident(
                "transporteur", offset, LATE_CARRIER[0]
            ):
                self.delayed.append(order)  # le camion ne passe qu'au prochain jour d'expédition
                continue
            shipment = self._prepare(order)
            if shipment is not None:
                temperature = Decimal(self.rng.choice(["2.1", "2.6", "3.0", "3.4"]))
                shipping.ship_order(
                    shipment, carrier="Transports Frigo Atlantique", temperature=temperature
                )

    def _pending_demand(self, article: Article, day: date) -> Decimal:
        """Quantités des commandes des autres données de démonstration (EDI des derniers jours)
        à expédier ce jour-là : la production les prévoit aussi."""
        total = (
            CustomerOrderLine.objects.filter(
                article=article,
                order__status=OrderStatus.RECEIVED,
                order__ship_by_date=day,
            )
            .exclude(order__customer_reference__startswith=f"{REFERENCE}-")
            .aggregate(total=Sum("quantity"))["total"]
        )
        return total or ZERO

    def _ship_pending(self, day: date) -> None:
        """Commandes des autres données de démonstration (EDI des derniers jours…) arrivées à
        leur date limite d'expédition : la plateforme les expédie aussi. Celles reçues
        aujourd'hui restent à préparer dans l'application."""
        pending = (
            CustomerOrder.objects.filter(
                status=OrderStatus.RECEIVED,
                ship_by_date=day,
                received_at__lte=timezone.now(),
            )
            .exclude(customer_reference__startswith=f"{REFERENCE}-")
            .select_related("customer")
        )
        for order in pending:
            shipment = self._prepare(order)
            if shipment is not None:
                shipping.ship_order(
                    shipment, carrier="Transports Frigo Atlantique", temperature=Decimal("2.8")
                )

    def _ship_delayed(self, day: date) -> None:
        for order in self.delayed:
            shipment = self._prepare(order)
            if shipment is not None:
                shipping.ship_order(shipment, carrier=LATE_CARRIER[2], temperature=Decimal("2.9"))
        self.delayed = []

    # --- Invendables et matières périmées -------------------------------------------------

    def _dispose_unsellable(self, day: date) -> None:
        """Produit fini que plus aucune enseigne n'acceptera à la prochaine livraison : don ou
        destruction."""
        lots = Lot.objects.filter(
            article__in=self.products.values(),
            status=LotStatus.RELEASED,
            created_at__lte=timezone.now(),
        ).select_related("article")
        for lot in lots:
            if lot.quantity <= 0:
                continue
            buyers = self.buyers[lot.article.code]
            pct = min((customer.min_remaining_shelf_life_pct for customer in buyers), default=0)
            # Prochain jour d'expédition et sa livraison (calendrier)
            delivery = self._delivery(calendar.next_open_day(day, Activity.SHIPPING, strict=True))
            if lot.expiry_date >= delivery + timedelta(
                days=_days(Decimal(lot.article.shelf_life_days) * pct / 100)
            ):
                continue
            reason = "DLC trop courte pour toutes les enseignes"
            lot = stock_services.block_lot(lot, reason=reason)
            destination = (
                UnsoldDestination.DONATION
                if lot.expiry_date >= day + timedelta(days=2)
                else UnsoldDestination.DESTRUCTION
            )
            stock_services.dispose_unsold(lot, destination=destination, reason=reason)

    def _destroy_expired_materials(self, day: date) -> None:
        lots = Lot.objects.filter(
            article__article_type__in=[ArticleType.RAW_MATERIAL, ArticleType.SEMI_FINISHED],
            status=LotStatus.RELEASED,
            expiry_date__lt=day + timedelta(days=1),
            created_at__lte=timezone.now(),
        )
        for lot in lots:
            if lot.quantity <= 0:
                continue
            lot = stock_services.block_lot(lot, reason="DLC atteinte : matière inutilisable")
            stock_services.destroy_lot(lot, reason="DLC atteinte : destruction")


@transaction.atomic
def load_demo_data(days: int = HISTORY_DAYS) -> dict[str, int | str]:
    if CustomerOrder.objects.filter(customer_reference__startswith=f"{REFERENCE}-").exists():
        return {"historique": "déjà présent, non modifié"}
    missing = [code for code in DAILY_DEMAND if not Article.objects.filter(code=code).exists()]
    if missing:
        raise ValidationError(f"Référentiel incomplet pour l'historique : {', '.join(missing)}.")
    return History(days).run()
