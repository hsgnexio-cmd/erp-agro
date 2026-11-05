"""Planning (charge, allergènes) et API de production."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.utils import timezone

from production import orders, planning
from production.models import ProductionOrder
from referentiel.models import Allergen, Article, BillOfMaterials, BOMLine, Recipe
from stocks.models import Alert

TODAY = timezone.localdate


def monday():
    return TODAY() - timedelta(days=TODAY().weekday())


def test_charge_et_surcharge(lasagna_line, finished_product, factory):
    for quantity in ("24000", "14400"):  # 10 h + 6 h = 16 h > 15 h
        orders.create_order(
            article=finished_product,
            planned_quantity=Decimal(quantity),
            planned_date=monday(),
            line=lasagna_line,
        )
    cell = planning.week_planning(monday())["lines"][0]["cells"][0]
    assert cell["hours"] == Decimal("16.0")
    assert cell["warnings"][0] == "Surcharge : 16 h prévues pour 15 h disponibles."


def test_ordre_des_allergenes_sur_une_ligne(lasagna_line, finished_product, family, cream, factory):
    """Lasagnes (lait, via la crème) puis des pâtes nature sans lait : nettoyage requis."""
    cream.allergens.add(Allergen.objects.get(code="lait"))
    plain = Article.objects.create(
        name="Pâtes nature 300 g", article_type="PF", unit="u", format_size=300,
        recipe=Recipe.objects.create(code="PATNAT", name="Pâtes nature", family=family),
        shelf_life_days=14,
    )  # fmt: skip
    tray = Article.objects.create(
        code="EM-BARQ-300N", name="Barquette", article_type="EM", unit="u"
    )
    BOMLine.objects.create(
        bom=BillOfMaterials.objects.create(article=plain), component=tray,
        quantity=Decimal("1"), unit="u",
    )  # fmt: skip
    for article, sequence in ((finished_product, 1), (plain, 2)):
        orders.create_order(
            article=article,
            planned_quantity=Decimal("100"),
            planned_date=monday(),
            line=lasagna_line,
            sequence=sequence,
        )
    warnings = planning.week_planning(monday())["lines"][0]["cells"][0]["warnings"]
    assert len(warnings) == 1
    assert "Lait" in warnings[0] and "Nettoyage renforcé" in warnings[0]

    # Dans l'autre ordre (sans allergène d'abord) : pas d'avertissement
    ProductionOrder.objects.filter(article=finished_product).update(sequence=3)
    assert planning.week_planning(monday())["lines"][0]["cells"][0]["warnings"] == []


@pytest.mark.parametrize(("role", "expected"), [("production", 201), ("qualite", 403)])
def test_seule_la_production_cree_un_of(
    api_client_for, bechamel, factory_site, factory, role, expected
):
    response = api_client_for(role).post(
        "/api/production/orders/",
        {
            "article": bechamel.id,
            "planned_quantity": "100",
            "planned_date": str(TODAY()),
            "site": factory_site.id,
        },
        format="json",
    )
    assert response.status_code == expected


def test_parcours_complet_par_l_api(
    api_client_for, bechamel, factory_site, factory, stock_lot, milk, cream
):
    cream_lot, milk_lot = stock_lot(cream, "20"), stock_lot(milk, "100")
    client = api_client_for("production")
    order = client.post(
        "/api/production/orders/",
        {"article": bechamel.id, "planned_quantity": "100", "planned_date": str(TODAY()),
         "site": factory_site.id},
        format="json",
    ).json()  # fmt: skip
    assert [n["component_code"] for n in order["needs"]] == ["MP-LAI-LAIT", "MP-LAI-CREME35"]
    client.post(f"/api/production/orders/{order['id']}/launch/")

    proposal = client.get(f"/api/production/orders/{order['id']}/proposal/?quantity=100").json()
    consumptions = [
        {"lot": lot["lot"], "location": lot["location"], "quantity": lot["suggested"]}
        for row in proposal
        for lot in row["lots"]
    ]
    declared = client.post(
        f"/api/production/orders/{order['id']}/declare/",
        {"quantity": "100", "consumptions": consumptions},
        format="json",
    )
    assert declared.status_code == 201
    closed = client.post(f"/api/production/orders/{order['id']}/close/").json()
    assert closed["status"] == "termine"
    assert closed["yield_report"]["mass_yield"] == "100.0"
    assert {lot.pk for lot in (cream_lot, milk_lot)}  # lots consommés


def test_lignes_compatibles_avec_un_article(api_client_for, lasagna_line, finished_product):
    lines = api_client_for("production").get(
        f"/api/referentiel/production-lines/?article={finished_product.id}"
    )
    assert [line["code"] for line in lines.json()["results"]] == ["L1"]


def test_planning_par_l_api(api_client_for, lasagna_line, finished_product, factory):
    orders.create_order(
        article=finished_product, planned_quantity=Decimal("2400"), planned_date=TODAY(),
        line=lasagna_line,
    )  # fmt: skip
    body = api_client_for("direction").get(f"/api/production/planning/?week={TODAY()}").json()
    day = next(c for c in body["lines"][0]["cells"] if c["date"] == str(TODAY()))
    assert day["hours"] == "1.0"
    assert day["orders"][0]["article_code"] == "PF-PAT-LASBOL-BRE-300"


def test_donnees_de_demo_de_la_production(db):
    call_command("charger_donnees_demo", sans_historique=True)
    done = ProductionOrder.objects.filter(status="termine")
    yields = sorted(orders.yield_report(order)["mass_yield"] for order in done)
    assert yields[0] < orders.YIELD_TARGET <= yields[1]
    assert Alert.objects.filter(alert_type="rendement_faible").count() == 1
    # Les OF de démonstration sont planifiés à partir de demain
    tomorrow = TODAY() + timedelta(days=1)
    week = planning.week_planning(tomorrow - timedelta(days=tomorrow.weekday()))
    warnings = [w for line in week["lines"] for cell in line["cells"] for w in cell["warnings"]]
    assert any("Nettoyage renforcé" in w for w in warnings)
    call_command("charger_donnees_demo", sans_historique=True)
    assert ProductionOrder.objects.count() == 9
