"""Ordres de fabrication : lignes, statuts, déclaration FEFO (règle 4), rendement."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from production import orders
from production.models import OrderStatus
from qualite import services as quality
from referentiel.models import Article, BillOfMaterials
from stocks.choices import AlertType, LotStatus
from stocks.models import Alert

TODAY = timezone.localdate


@pytest.fixture
def bechamel_order(bechamel, factory_site, factory):
    order = orders.create_order(
        article=bechamel, planned_quantity=Decimal("100"), planned_date=TODAY(), site=factory_site
    )
    return orders.launch_order(order)


def consumption(lot, location, quantity, justification=""):
    return {
        "lot": lot,
        "location": location,
        "quantity": Decimal(quantity),
        "justification": justification,
    }


# --- Création -----------------------------------------------------------------


def test_besoins_theoriques_avec_pertes(bechamel):
    needs = {n.component.code: n for n in orders.theoretical_needs(bechamel, Decimal("200"))}
    assert needs["MP-LAI-LAIT"].gross == Decimal("140.000")
    # 20 kg nets de crème avec 5 % de perte → 21,053 kg bruts
    assert needs["MP-LAI-CREME35"].net == Decimal("20.000")
    assert needs["MP-LAI-CREME35"].gross == Decimal("21.053")


def test_un_of_de_semi_fini_sort_en_chambre_froide_semi_finis(bechamel_order):
    assert bechamel_order.number.startswith("OF-")
    assert bechamel_order.output_location.code == "NAN-CF-SF"
    assert bechamel_order.status == OrderStatus.LAUNCHED


def test_un_produit_fini_sur_une_ligne_compatible(lasagna_line, finished_product, factory):
    order = orders.create_order(
        article=finished_product,
        planned_quantity=Decimal("2000"),
        planned_date=TODAY(),
        line=lasagna_line,
    )
    assert order.site == lasagna_line.site
    assert order.output_location.code == "PFN-QUAR"


def test_ligne_incompatible_avec_le_format(lasagna_line, finished_product, recipe, factory):
    family_pack = Article.objects.create(
        name="Lasagnes 1 kg", article_type="PF", unit="u", recipe=recipe,
        format_size=1000, shelf_life_days=14,
    )  # fmt: skip
    BillOfMaterials.objects.create(article=family_pack)
    with pytest.raises(ValidationError) as exc:
        orders.create_order(
            article=family_pack,
            planned_quantity=Decimal("500"),
            planned_date=TODAY(),
            line=lasagna_line,
        )
    assert "300 g" in exc.value.message_dict["line"][0]


def test_un_produit_fini_exige_une_ligne(lasagna_line, finished_product, factory_site, factory):
    with pytest.raises(ValidationError) as exc:
        orders.create_order(
            article=finished_product,
            planned_quantity=Decimal("10"),
            planned_date=TODAY(),
            site=factory_site,
        )
    assert "line" in exc.value.message_dict


def test_modifier_seulement_un_of_planifie(bechamel, factory_site, factory):
    order = orders.create_order(
        article=bechamel, planned_quantity=Decimal("100"), planned_date=TODAY(), site=factory_site
    )
    order = orders.update_order(order, planned_quantity=Decimal("150"))
    assert order.planned_quantity == Decimal("150")
    orders.launch_order(order)
    with pytest.raises(ValidationError):
        orders.update_order(order, planned_quantity=Decimal("200"))


# --- Proposition FEFO et déclaration -------------------------------------------------


def test_la_proposition_suit_le_fefo(bechamel_order, stock_lot, milk, cream):
    late = stock_lot(cream, "50", expiry_in=15)
    early = stock_lot(cream, "8", expiry_in=5)
    stock_lot(milk, "200")

    rows = {
        row["need"].component.code: row for row in orders.proposal(bechamel_order, Decimal("100"))
    }
    cream_row = rows["MP-LAI-CREME35"]
    assert [item["lot"] for item in cream_row["lots"]] == [early, late]
    # Besoin brut 10,526 kg : 8 kg du lot qui périme d'abord, le reste du suivant
    assert [item["suggested"] for item in cream_row["lots"]] == [Decimal("8"), Decimal("2.526")]
    assert rows["MP-LAI-LAIT"]["missing"] == 0


def test_declaration_cree_un_lot_trace(bechamel_order, stock_lot, milk, cream, factory):
    cream_lot, milk_lot = stock_lot(cream, "20"), stock_lot(milk, "100")
    room = factory["NAN-CF-MP"]
    declaration = orders.declare_production(
        bechamel_order,
        quantity=Decimal("100"),
        consumptions=[
            consumption(cream_lot, room, "10.5"),
            consumption(milk_lot, room, "70"),
        ],
    )
    lot = declaration.lot
    assert lot.number.startswith("LF-")
    assert lot.status == LotStatus.QUARANTINE
    assert lot.location.code == "NAN-CF-SF"
    # Règle 1 : la traçabilité amont retrouve les lots consommés
    upstream = {child.lot for child in quality.upstream(lot).children}
    assert upstream == {cream_lot, milk_lot}


def test_un_lot_hors_fefo_exige_une_justification(bechamel_order, stock_lot, milk, cream, factory):
    early = stock_lot(cream, "20", expiry_in=5)
    late = stock_lot(cream, "20", expiry_in=15)
    milk_lot = stock_lot(milk, "100")
    room = factory["NAN-CF-MP"]
    lines = [consumption(late, room, "10.5"), consumption(milk_lot, room, "70")]

    with pytest.raises(ValidationError) as exc:
        orders.declare_production(bechamel_order, quantity=Decimal("100"), consumptions=lines)
    assert early.number in exc.value.message_dict["consumptions"][0]

    lines[0]["justification"] = "Lot proposé introuvable dans la chambre froide"
    declaration = orders.declare_production(
        bechamel_order, quantity=Decimal("100"), consumptions=lines
    )
    assert declaration.fefo_deviations[0]["lot_number"] == late.number
    assert declaration.fefo_deviations[0]["proposed"] == [early.number]
    movement = late.movements.get(movement_type="consommation")
    assert movement.reason.startswith("Hors FEFO")


def test_on_ne_declare_que_sur_un_of_lance(bechamel, factory_site, factory, stock_lot, milk):
    order = orders.create_order(
        article=bechamel, planned_quantity=Decimal("100"), planned_date=TODAY(), site=factory_site
    )
    with pytest.raises(ValidationError):
        orders.declare_production(
            order,
            quantity=Decimal("1"),
            consumptions=[consumption(stock_lot(milk, "10"), factory["NAN-CF-MP"], "1")],
        )


def test_plusieurs_declarations_puis_cloture(bechamel_order, stock_lot, milk, cream, factory):
    cream_lot, milk_lot = stock_lot(cream, "30"), stock_lot(milk, "200")
    room = factory["NAN-CF-MP"]
    for _ in range(2):  # une déclaration par équipe
        orders.declare_production(
            bechamel_order,
            quantity=Decimal("50"),
            consumptions=[consumption(cream_lot, room, "5.263"), consumption(milk_lot, room, "35")],
        )
    assert orders.produced_quantity(bechamel_order) == Decimal("100")
    order = orders.close_order(bechamel_order)
    assert order.status == OrderStatus.DONE
    assert orders.yield_report(order)["mass_yield"] == Decimal("100.0")


# --- Rendement -----------------------------------------------------------------------


def test_rendement_faible_signale_et_alerte(bechamel_order, stock_lot, milk, cream, factory):
    cream_lot, milk_lot = stock_lot(cream, "30"), stock_lot(milk, "200")
    room = factory["NAN-CF-MP"]
    orders.declare_production(
        bechamel_order,
        quantity=Decimal("100"),
        consumptions=[consumption(cream_lot, room, "11.5"), consumption(milk_lot, room, "75")],
    )
    report = orders.yield_report(bechamel_order)
    milk_row = next(r for r in report["components"] if r["component"].code == "MP-LAI-LAIT")
    assert milk_row["theoretical"] == Decimal("70.000")
    assert milk_row["gap_pct"] == Decimal("7.1")
    # (70 + 10,526) ÷ (75 + 11,5) = 93,1 %
    assert report["mass_yield"] == Decimal("93.1")
    assert report["below_target"]

    orders.close_order(bechamel_order)
    alert = Alert.objects.get(alert_type=AlertType.LOW_YIELD)
    assert bechamel_order.number in alert.message


def test_annuler_seulement_sans_declaration(bechamel_order, stock_lot, milk, factory):
    orders.declare_production(
        bechamel_order,
        quantity=Decimal("1"),
        consumptions=[consumption(stock_lot(milk, "10"), factory["NAN-CF-MP"], "0.7")],
    )
    with pytest.raises(ValidationError):
        orders.cancel_order(bechamel_order)


def test_cloturer_exige_une_declaration(bechamel_order):
    with pytest.raises(ValidationError):
        orders.close_order(bechamel_order)
    assert orders.cancel_order(bechamel_order).status == OrderStatus.CANCELLED


def test_dlc_du_lot_fabrique(bechamel_order, stock_lot, milk, factory):
    """Règle 3 : la béchamel a 3 jours de durée de vie."""
    declaration = orders.declare_production(
        bechamel_order,
        quantity=Decimal("1"),
        consumptions=[consumption(stock_lot(milk, "10"), factory["NAN-CF-MP"], "0.7")],
    )
    assert declaration.lot.expiry_date == TODAY() + timedelta(days=3)
