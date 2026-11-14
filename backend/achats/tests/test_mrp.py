"""Calcul des besoins (MRP, phase 9c) : éclatement, besoins nets, propositions, commandes."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from achats import mrp
from achats.models import PurchaseOrder
from achats.tests.conftest import reference
from previsions.forecast import current_week
from previsions.models import ForecastLine, ForecastVersion
from production import master_plan
from production import orders as production
from referentiel.choices import SiteType, TemperatureClass
from referentiel.models import (
    BillOfMaterials,
    BOMLine,
    Location,
    ProductionLine,
    Site,
    Supplier,
)
from stocks import services as stock_services

D = Decimal
TODAY = timezone.localdate


def week(offset: int) -> date:
    return current_week() + timedelta(days=7 * offset)


@pytest.fixture
def world(warehouse, quarantine_zones, factory_site, family, finished_product, semi_finished,
          cream, tray, private_label_customer):  # fmt: skip
    """Lasagnes = 0,1 kg de béchamel + 1 barquette ; béchamel = 20 % de crème.

    Prévision : 10 000 lasagnes par semaine de S+1 à S+8 (version figée lundi)."""
    bechamel = BillOfMaterials.objects.create(article=semi_finished, base_quantity=D("100"))
    BOMLine.objects.create(bom=bechamel, component=cream, quantity=D("20"), unit="kg")
    lasagna = BillOfMaterials.objects.create(article=finished_product)
    BOMLine.objects.create(bom=lasagna, component=semi_finished, quantity=D("0.1"), unit="kg")
    BOMLine.objects.create(bom=lasagna, component=tray, quantity=D("1"), unit="u")
    line = ProductionLine.objects.create(
        code="L1", name="Pâtes 300 g", site=factory_site, formats=[300], capacity_per_hour=2400
    )
    line.families.add(family)
    for code in ("NAN-CF-SF", "NAN-CF-MP"):
        Location.objects.create(
            site=factory_site, code=code, name=code, temperature_class=TemperatureClass.CHILLED
        )
    platform = Site.objects.create(code="PFN", name="Plateforme", site_type=SiteType.PLATFORM)
    Location.objects.create(
        site=platform, code="PFN-QUAR", name="Quarantaine",
        temperature_class=TemperatureClass.CHILLED,
    )  # fmt: skip
    version = ForecastVersion.objects.create(
        number="PRV-T-1",
        created_at=timezone.make_aware(datetime.combine(week(0), time(5))),
        source="auto",
        first_week=week(1),
    )
    for offset in range(1, 9):
        ForecastLine.objects.create(
            version=version, customer=private_label_customer, article=finished_product,
            week=week(offset), base_quantity=D("10000"), quantity=D("10000"),
        )  # fmt: skip
    dairy_supplier = Supplier.objects.create(
        code="FOU-005", name="Crèmerie", lead_time_days=3, audited=True,
        last_audit_date=date(2026, 3, 1),
    )  # fmt: skip
    packaging_supplier = Supplier.objects.create(
        code="FOU-013", name="Emballages", lead_time_days=35, audited=True,
        last_audit_date=date(2026, 3, 1),
    )  # fmt: skip
    reference(dairy_supplier, cream, price="4.20", minimum=D("500"))
    reference(packaging_supplier, tray, price="0.08", minimum=D("5000"))
    return {
        "line": line, "dairy": dairy_supplier, "packaging": packaging_supplier,
        "cream": cream, "tray": tray, "bechamel": semi_finished, "lasagna": finished_product,
    }  # fmt: skip


def stock(article, quantity, location):
    lot = stock_services.receive_lot(
        article=article, supplier=None, quantity=D(quantity), location=location,
        reception_date=TODAY(), expiry_date=TODAY() + timedelta(days=20),
        supplier_lot_number="", block_reasons=[], user=None, reference="TEST",
    )  # fmt: skip
    return stock_services.release_lot(lot)


def row_of(result, article):
    return next(row for row in result.articles if row.article == article)


def cells(result, article):
    return {cell.week: cell for cell in row_of(result, article).weeks}


def proposals_of(result, article):
    return [p for p in result.proposals if p.article == article]


# --- Éclatement et besoins bruts --------------------------------------------------------


def test_horizon_semaine_en_cours_plus_huit_et_origine_des_quantites(world):
    result = mrp.compute()
    assert result.weeks == [week(k) for k in range(9)]
    assert result.sources[week(0)] == "OF de la semaine"
    assert result.sources[week(1)] == "prévision PRV-T-1"


def test_eclatement_a_tous_les_niveaux(world):
    result = mrp.compute()
    # 10 000 lasagnes → 1 000 kg de béchamel → 200 kg de crème ; 10 000 barquettes
    assert cells(result, world["cream"])[week(1)].gross == D("200.000")
    assert cells(result, world["tray"])[week(1)].gross == D("10000.000")
    assert cells(result, world["cream"])[week(0)].gross == D("0")


def test_stock_de_semi_fini_deduit_avant_eclatement(world, quarantine_zones):
    stock(world["bechamel"], "500", quarantine_zones[TemperatureClass.CHILLED])
    result = mrp.compute()
    # 1 000 kg de béchamel nécessaires, 500 en stock : seulement 100 kg de crème en S+1
    assert cells(result, world["cream"])[week(1)].gross == D("100.000")
    assert cells(result, world["cream"])[week(2)].gross == D("200.000")


def test_plan_brouillon_prioritaire_sur_la_prevision(world):
    plan, _ = master_plan.compute_plan(week(1))
    for day in master_plan.work_days(week(1)):
        master_plan.set_quantity(plan, article=world["lasagna"], day=day, quantity=D("1000"))
    result = mrp.compute()
    assert result.sources[week(1)] == "plan brouillon"
    assert cells(result, world["tray"])[week(1)].gross == D("5000.000")


def test_of_ouverts_de_la_semaine_comptent(world):
    production.create_order(
        article=world["lasagna"], planned_quantity=D("2000"), planned_date=TODAY(),
        line=world["line"],
    )  # fmt: skip
    result = mrp.compute()
    assert cells(result, world["tray"])[week(0)].gross == D("2000.000")


# --- Besoins nets et propositions ---------------------------------------------------------


def test_besoin_net_apres_stock_et_minimum_de_commande(world, quarantine_zones):
    stock(world["cream"], "150", quarantine_zones[TemperatureClass.CHILLED])
    result = mrp.compute()
    first, second = proposals_of(result, world["cream"])[:2]
    # S+1 : 200 − 150 = 50 kg manquants, relevés au minimum de 500 kg
    assert (first.week, first.net, first.quantity, first.raised_to_minimum) == (
        week(1), D("50.000"), D("500"), True,
    )  # fmt: skip
    assert first.order_date == week(1) - timedelta(days=3)
    assert first.unit_price == D("4.2000") and first.amount == D("2100.00")
    # Reste 450 : S+2 et S+3 couvertes, nouvelle commande en S+4
    assert second.week == week(4)
    assert cells(result, world["cream"])[week(3)].projected == D("50.000")


def test_commande_en_cours_deduite_et_brouillon_compris(world, make_order):
    make_order((world["tray"], "6000"), supplier=world["packaging"], send=False,
               expected_delivery_date=week(1))  # fmt: skip
    result = mrp.compute()
    tray = cells(result, world["tray"])
    assert tray[week(1)].receipts == D("6000.000")
    assert proposals_of(result, world["tray"])[0].net == D("4000.000")


def test_delai_long_proposition_en_retard(world):
    tray = proposals_of(mrp.compute(), world["tray"])[0]
    # Emballage : 35 jours de délai, besoin la semaine prochaine → il fallait commander avant
    assert tray.order_date == week(1) - timedelta(days=35)
    assert tray.late is True


def test_fournisseur_principal_non_audite_remplace_par_un_audite(world):
    link = world["cream"].supplier_links.get(supplier=world["dairy"])
    link.is_main_supplier = False
    link.save()
    unaudited = Supplier.objects.create(code="FOU-099", name="Non audité", lead_time_days=1)
    reference(unaudited, world["cream"])  # fournisseur principal, mais pas audité
    assert mrp.choose_supplier(world["cream"]).supplier == world["dairy"]


# --- Création des commandes --------------------------------------------------------------


def test_une_commande_brouillon_par_fournisseur_et_par_semaine(world, make_user):
    result = mrp.compute()
    selections = [
        {"article": p.article, "week": p.week, "quantity": p.quantity}
        for p in result.proposals
        if p.week in (week(1), week(2))
    ]
    created = mrp.create_orders(selections, user=make_user("acheteur"))
    # Crème : le minimum de 500 kg couvre S+1 et S+2, une seule commande
    assert {(o.supplier.code, o.expected_delivery_date) for o in created} == {
        # 3 jours de délai : le week-end, la crème ne peut pas arriver dès le lundi
        ("FOU-005", max(TODAY() + timedelta(days=3), week(1))),
        ("FOU-013", TODAY() + timedelta(days=35)),  # pas avant le délai du fournisseur
        ("FOU-013", max(TODAY() + timedelta(days=35), week(2))),
    }  # fmt: skip
    assert all(o.status == "brouillon" and "MRP" in o.comment for o in created)
    assert created[0].created_by.username == "user-acheteur"
    # Recalcul : les commandes brouillon couvrent ces semaines
    after = mrp.compute()
    assert not [p for p in proposals_of(after, world["cream"]) if p.week == week(1)]


def test_creation_refusee_pour_un_produit_fini_ou_sans_fournisseur(world, flour):
    with pytest.raises(ValidationError) as exc:
        mrp.create_orders([
            {"article": world["lasagna"], "week": week(1), "quantity": D("10")},
            {"article": flour, "week": week(1), "quantity": D("10")},
        ])  # fmt: skip
    messages = exc.value.messages
    assert any("seules les matières" in m for m in messages)
    assert any("aucun fournisseur audité" in m for m in messages)
    assert PurchaseOrder.objects.count() == 0
    with pytest.raises(ValidationError):
        mrp.create_orders([])


def test_minimum_de_commande_toujours_controle(world):
    with pytest.raises(ValidationError) as exc:
        mrp.create_orders([{"article": world["cream"], "week": week(1), "quantity": D("100")}])
    assert "Quantité minimale" in str(exc.value)


# --- API ---------------------------------------------------------------------------------


def test_api_la_production_consulte_seul_l_acheteur_cree(world, api_client_for):
    # Matrice d'accès : la production consulte le MRP, le quai ne le voit pas
    assert api_client_for("magasinier").get("/api/achats/mrp/").status_code == 403
    production = api_client_for("production")
    response = production.get("/api/achats/mrp/")
    assert response.status_code == 200
    data = response.json()
    assert len(data["weeks"]) == 9 and data["weeks"][1]["source"] == "prévision PRV-T-1"
    proposal = next(p for p in data["proposals"] if p["article_code"] == "EM-BARQ-300N")
    assert proposal["late"] is True and proposal["supplier_code"] == "FOU-013"

    payload = {"selections": [
        {"article": world["cream"].pk, "week": str(week(1)), "quantity": "500"}
    ]}  # fmt: skip
    assert (
        production.post("/api/achats/mrp/create-orders/", payload, format="json").status_code == 403
    )
    response = api_client_for("acheteur").post(
        "/api/achats/mrp/create-orders/", payload, format="json"
    )
    assert response.status_code == 201, response.json()
    assert response.json()[0]["number"].startswith("CA-")


def test_emballage_commande_en_unites_entieres(world):
    # Une prévision figée ne se modifie pas : on passe par un OF de la semaine en cours
    production.create_order(
        article=world["lasagna"], planned_quantity=D("2000.5"), planned_date=TODAY(),
        line=world["line"],
    )  # fmt: skip
    tray = proposals_of(mrp.compute(), world["tray"])[0]
    assert tray.week == week(0)
    assert tray.net == D("2000.500")
    assert tray.quantity == D("5000")  # minimum de commande
    world["tray"].supplier_links.update(min_order_quantity=None)
    tray = proposals_of(mrp.compute(), world["tray"])[0]
    assert tray.quantity == D("2001")
    assert tray.raised_to_minimum is False  # simple arrondi à l'unité
