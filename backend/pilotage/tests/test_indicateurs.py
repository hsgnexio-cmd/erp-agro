"""Indicateurs de pilotage (phase 8).

Les vues SQL du schéma « bi » (lues par le tableau de bord et par Power BI) doivent donner
exactement les mêmes résultats que les calculs métier en Python, sur des données connues.
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.db import connection
from django.utils import timezone

from achats.models import ReceptionLine, SupplierPrice
from achats.services import current_price
from pilotage import indicators
from pilotage.demo_history import simulated_clock
from production import orders as production
from production.models import OrderStatus, ProductionOrder
from qualite import services as quality
from referentiel.choices import SiteType, TemperatureClass
from referentiel.models import Location, Site, Supplier, SupplierArticle
from stocks import services as stock_services
from stocks.choices import LotStatus, MovementType
from stocks.models import Lot, StockMovement
from ventes import shipping
from ventes.models import ShipmentLine, ShipmentStatus


def _sql(query: str, params=()):
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchone()


def _by_code(items):
    return {item.code: item for item in items}


MARKDOWN_TYPES = ["destruction", "don", "alimentation_animale", "destruction_invendable"]


def _unit_value(lot: Lot, on_date: date) -> Decimal:
    """Valorisation de la phase 8, recalculée en Python : prix de vente moyen en vigueur pour
    un produit fini, prix d'achat du fournisseur du lot pour une matière."""
    if lot.article.article_type == "PF":
        prices = [
            price.unit_price
            for price in lot.article.sale_prices.filter(valid_from__lte=on_date)
            if price.valid_to is None or price.valid_to >= on_date
        ]
        return sum(prices) / len(prices)
    link = SupplierArticle.objects.get(supplier=lot.supplier, article=lot.article)
    return current_price(link, on_date).unit_price


@pytest.fixture
def demo(db):
    call_command("charger_donnees_demo", sans_historique=True)


def test_indicateurs_identiques_aux_calculs_metier_sur_la_demo(demo):
    today = timezone.localdate()
    start, end = today - timedelta(days=29), today + timedelta(days=7)
    kpi = _by_code(indicators.compute(start, end))

    # Taux de service : même résultat que l'écran du taux de service (ventes)
    expected = shipping.service_rate(start=start, end=end)
    assert kpi["service_rate"].value == expected["total"]["rate"]
    for row in expected["customers"]:
        value, _ = indicators.service_rate(start, end, row["customer"].pk)
        assert value == row["rate"], row["customer"].code

    # Rendement matière : théorique ÷ réel des OF terminés (yield_report)
    theoretical = actual = Decimal("0")
    for order in ProductionOrder.objects.filter(status=OrderStatus.DONE):
        for component in production.yield_report(order)["components"]:
            if component["unit"] in production.MASS_UNITS:
                theoretical += component["theoretical"]
                actual += component["actual"]
    assert kpi["material_yield"].value == (theoretical / actual * 100).quantize(Decimal("0.1"))

    # Conformité réception : lignes conformes ÷ lignes reçues
    lines = ReceptionLine.objects.all()
    compliant = lines.filter(is_compliant=True).count()
    assert kpi["reception_compliance"].value == (Decimal(compliant) / lines.count() * 100).quantize(
        Decimal("0.1")
    )

    # Démarque : sorties « destruction », « don »… valorisées ÷ chiffre d'affaires expédié
    lost = sum(
        -movement.quantity * _unit_value(movement.lot, today)
        for movement in StockMovement.objects.filter(movement_type__in=MARKDOWN_TYPES)
    )
    assert lost == Decimal("4715.40")  # bœuf détruit (600 kg × 7,80 €) + 6 gratins à 5,90 €
    revenue = sum(
        line.quantity * line.order_line.unit_price
        for line in ShipmentLine.objects.filter(shipment__status=ShipmentStatus.SHIPPED)
    )
    assert kpi["markdown"].value == (lost / revenue * 100).quantize(Decimal("0.01"))

    # Délai de traçabilité : mesuré, très loin des 5 minutes
    assert kpi["traceability"].status == "ok"
    assert kpi["traceability"].value < 2

    # TRS : calculable, mais aucune plage de marche déclarée sans l'historique
    assert kpi["oee"].status == "sans_donnee"
    assert kpi["oee"].value is None
    # Fiabilité des prévisions : calculable, mais aucune version figée sans l'historique
    assert kpi["forecast_accuracy"].status == "sans_donnee"


def test_couverture_produits_finis_stock_disponible_sur_sorties_moyennes(demo):
    today = timezone.localdate()
    value, _ = indicators._coverage(today, today, ["PF"], "expedition", None)

    stock = sum(
        lot.quantity * _unit_value(lot, today)
        for lot in Lot.objects.filter(
            article__article_type="PF", status__in=[LotStatus.RELEASED, LotStatus.QUARANTINE]
        )
    )
    shipped = sum(
        -movement.quantity * _unit_value(movement.lot, today)
        for movement in StockMovement.objects.filter(movement_type=MovementType.SHIPMENT)
    )
    # Toutes les expéditions de la démo sont d'aujourd'hui : sorties moyennes = sorties du jour
    assert value == (stock / shipped).quantize(Decimal("0.1"))


def test_lancement_d_un_rappel_garde_la_duree_du_calcul(demo):
    lot = Lot.objects.get(supplier_lot_number="CB-0412")
    recall = quality.launch_recall(lot, reason="Test de durée")
    assert isinstance(recall.snapshot["duration_ms"], int)
    number, duration = _sql("SELECT recall_number, duration_ms FROM bi.fact_recall")
    assert number == recall.number
    assert duration == recall.snapshot["duration_ms"]


# --- Stock jour par jour : statut d'un jour passé retrouvé dans le journal ---------------


@pytest.fixture
def cream_room(db):
    warehouse = Site.objects.create(code="MPE", name="Entrepôt", site_type=SiteType.WAREHOUSE)
    return Location.objects.create(
        site=warehouse, code="MPE-FP-01", name="Froid", temperature_class=TemperatureClass.CHILLED
    )


def test_stock_du_jour_avec_le_statut_du_lot_ce_jour_la(cream, cream_room):
    today = timezone.localdate()
    supplier = Supplier.objects.create(
        code="FOU-004", name="Crèmerie", lead_time_days=3, audited=True, last_audit_date=today
    )
    link = SupplierArticle.objects.create(supplier=supplier, article=cream, is_main_supplier=True)
    SupplierPrice.objects.create(
        supplier_article=link, unit_price=Decimal("4.20"), valid_from=today - timedelta(days=30)
    )

    def at(days_ago: int):
        day = today - timedelta(days=days_ago)
        return simulated_clock(timezone.make_aware(datetime.combine(day, time(10))))

    with at(3):
        lot = stock_services.receive_lot(
            article=cream, supplier=supplier, quantity=Decimal("100"), location=cream_room,
            reception_date=today - timedelta(days=3), expiry_date=today + timedelta(days=15),
            supplier_lot_number="CB-1", block_reasons=[], user=None, reference="REC-TEST",
        )  # fmt: skip
    with at(2):
        stock_services.release_lot(lot, reason="Contrôle conforme")
    with at(1):
        stock_services.block_lot(lot, reason="Suspicion de contamination")

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT date, lot_status, quantity, bi.unit_value(article_id, NULL, date) "
            "FROM bi.fact_stock_daily ORDER BY date"
        )
        rows = cursor.fetchall()
    assert [(row[0], row[1]) for row in rows] == [
        (today - timedelta(days=3), "quarantaine"),
        (today - timedelta(days=2), "libere"),
        (today - timedelta(days=1), "bloque"),
        (today, "bloque"),
    ]
    assert {row[2] for row in rows} == {Decimal("100")}
    assert {row[3] for row in rows} == {Decimal("4.20")}


# --- API -----------------------------------------------------------------------------------


def test_tous_les_roles_consultent_les_indicateurs(demo, api_client_for):
    for role in ("direction", "magasinier", "commercial"):
        response = api_client_for(role).get("/api/pilotage/indicators/")
        assert response.status_code == 200, role
    data = response.json()
    assert [item["code"] for item in data["indicators"]] == [
        "service_rate", "markdown", "finished_coverage", "material_coverage",
        "material_yield", "oee", "forecast_accuracy", "reception_compliance", "traceability",
    ]  # fmt: skip
    service = data["indicators"][0]
    assert service["target"] == "≥ 98,5 %"
    assert service["target_min"] == "98.5"
    assert data["weeks"], "évolution par semaine"
    assert set(data["weeks"][0]["values"]) == set(indicators.WEEKLY_CODES)


def test_api_refuse_les_filtres_incoherents(api_client_for, factory_site):
    client = api_client_for("direction")
    response = client.get("/api/pilotage/indicators/?start=2026-11-05&end=2026-11-01")
    assert response.status_code == 400
    assert "La date de début est après la date de fin." in str(response.json())
    assert client.get("/api/pilotage/indicators/?site=999").status_code == 400
    ok = client.get(f"/api/pilotage/indicators/?site={factory_site.pk}&start=2026-10-01")
    assert ok.status_code == 200
    assert ok.json()["start"] == date(2026, 10, 1).isoformat()


def test_api_reservee_aux_utilisateurs_connectes(client):
    assert client.get("/api/pilotage/indicators/").status_code in (401, 403)


def test_export_csv_des_indicateurs_pour_excel(demo, api_client_for):
    # Période relative à aujourd'hui : les OF de la démo sont clôturés aujourd'hui
    end = timezone.localdate()
    start = end - timedelta(days=35)
    response = api_client_for("direction").get(
        f"/api/pilotage/indicators/export/?start={start}&end={end}"
    )
    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv; charset=utf-8"
    assert (
        f'filename="indicateurs-{start:%Y%m%d}-{end:%Y%m%d}.csv"' in response["Content-Disposition"]
    )
    content = response.content.decode("utf-8")
    assert content.startswith(f"﻿Indicateurs du {start:%d/%m/%Y} au {end:%d/%m/%Y}")
    lines = content.splitlines()
    assert "Indicateur;Valeur;Unité;Objectif;Statut;Détail" in lines
    trs = next(line for line in lines if line.startswith("TRS;"))
    assert ";Pas de donnée;" in trs  # aucune plage de marche sans historique
    # Décimales à la française pour Excel
    yield_line = next(line for line in lines if line.startswith("Rendement matière;"))
    assert "," in yield_line.split(";")[1]
    assert "Évolution par semaine" in lines
    first_week = f"S{start.isocalendar().week:02d} ({start:%d/%m})"
    assert any(line.startswith(f"Indicateur;Unité;{first_week}") for line in lines)
