"""Fabrication et expédition minimales : les règles qui garantissent la traçabilité."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from production.services import record_production
from referentiel.models import CustomerWarehouse
from stocks import services as stock_services
from stocks.choices import LotStatus, MovementType
from ventes.services import record_shipment


def test_la_fabrication_cree_un_lot_relie_aux_lots_consommes(chain, finished_product):
    lasagna = chain["lasagna"]

    assert lasagna.number.startswith("LF-")
    assert lasagna.production_date == timezone.localdate()
    # Règle 3 : DLC = date de fabrication + 14 jours de durée de vie
    assert lasagna.expiry_date == timezone.localdate() + timedelta(days=14)
    consumed = {m.lot.number for m in lasagna.consumptions.all()}
    assert consumed == {chain["bechamel"].number, chain["trays"].number}
    assert all(m.movement_type == MovementType.CONSUMPTION for m in lasagna.consumptions.all())
    assert chain["bechamel"].quantity == Decimal("110")  # 200 fabriqués − 90 consommés


def test_un_lot_fabrique_demarre_en_quarantaine(chain, semi_finished):
    lot = record_production(
        article=semi_finished,
        quantity=Decimal("10"),
        location=chain["cold"],
        consumptions=[
            {"lot": chain["cream_a"], "location": chain["cold"], "quantity": Decimal("1")}
        ],
    )
    assert lot.status == LotStatus.QUARANTINE


def test_on_ne_consomme_qu_un_lot_libere(chain, semi_finished):
    stock_services.block_lot(chain["cream_a"], reason="Analyse")
    with pytest.raises(ValidationError) as exc:
        record_production(
            article=semi_finished,
            quantity=Decimal("10"),
            location=chain["cold"],
            consumptions=[
                {"lot": chain["cream_a"], "location": chain["cold"], "quantity": Decimal("1")}
            ],
        )
    assert "non consommable" in exc.value.message_dict["consumptions"][0]


def test_on_ne_consomme_que_les_composants_de_la_nomenclature(chain, semi_finished):
    with pytest.raises(ValidationError) as exc:
        record_production(
            article=semi_finished,
            quantity=Decimal("10"),
            location=chain["cold"],
            consumptions=[
                {"lot": chain["lasagna"], "location": chain["cold"], "quantity": Decimal("1")}
            ],
        )
    assert "nomenclature" in exc.value.message_dict["consumptions"][0]


def test_on_ne_consomme_pas_plus_que_le_stock(chain, semi_finished):
    with pytest.raises(ValidationError):
        record_production(
            article=semi_finished,
            quantity=Decimal("10"),
            location=chain["cold"],
            consumptions=[
                {"lot": chain["cream_a"], "location": chain["cold"], "quantity": Decimal("81")}
            ],
        )


def test_l_expedition_est_reliee_a_l_entrepot_client(chain):
    shipment = chain["lasagna"].movements.get(movement_type=MovementType.SHIPMENT)
    assert shipment.customer_warehouse == chain["warehouse"]
    assert shipment.quantity == Decimal("-600")
    assert shipment.reference.startswith("EXP-")


def test_un_produit_mdd_ne_part_que_chez_son_enseigne(
    chain, recipe, private_label_customer, brand_only_customer
):
    """Les lasagnes Brévanne partent chez ENS2 ; une version MDD ENS2 ne part pas chez ENS4."""
    warehouse = CustomerWarehouse.objects.create(
        customer=brand_only_customer, code="ENS4-E01", name="Proxi", city="Nantes"
    )
    record_shipment(
        lot=chain["lasagna"], location=chain["cold"], quantity=Decimal("10"), warehouse=warehouse
    )
    from referentiel.models import Article

    mdd = Article.objects.create(
        name="Lasagnes MDD", article_type="PF", unit="u", recipe=recipe,
        brand_customer=private_label_customer, format_size=300, shelf_life_days=14,
    )  # fmt: skip
    from referentiel.models import BillOfMaterials

    BillOfMaterials.objects.create(article=mdd).lines.create(
        component=chain["bechamel"].article, quantity=Decimal("0.09"), unit="kg"
    )
    mdd_lot = stock_services.release_lot(
        record_production(
            article=mdd,
            quantity=Decimal("10"),
            location=chain["cold"],
            consumptions=[
                {"lot": chain["bechamel"], "location": chain["cold"], "quantity": Decimal("1")}
            ],
        )
    )
    with pytest.raises(ValidationError) as exc:
        record_shipment(
            lot=mdd_lot, location=chain["cold"], quantity=Decimal("1"), warehouse=warehouse
        )
    assert "MDD de ENS2" in exc.value.messages[0]


def test_dlc_minimale_client(chain):
    """Règle 5 : ENS2 exige 70 % de durée de vie restante à la livraison."""
    lasagna = chain["lasagna"]
    lasagna.expiry_date = timezone.localdate() + timedelta(days=9)  # 9/14 = 64 %
    lasagna.save()
    with pytest.raises(ValidationError) as exc:
        record_shipment(
            lot=lasagna, location=chain["cold"], quantity=Decimal("1"), warehouse=chain["warehouse"]
        )
    assert "trop court pour ENS2" in exc.value.messages[0]


def test_on_n_expedie_qu_un_lot_libere(chain):
    stock_services.block_lot(chain["lasagna"], reason="Analyse")
    with pytest.raises(ValidationError):
        record_shipment(
            lot=chain["lasagna"],
            location=chain["cold"],
            quantity=Decimal("1"),
            warehouse=chain["warehouse"],
        )
