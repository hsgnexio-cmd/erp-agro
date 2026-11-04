"""Préparation FEFO, expédition, palettes SSCC, taux de service (partie 7b)."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from qualite.services import downstream
from stocks import services as stock_services
from stocks.choices import AlertType, LotStatus, MovementType
from stocks.models import Alert, StockMovement
from ventes import orders, shipping
from ventes.models import OrderStatus, Shipment, ShipmentStatus

TODAY = timezone.localdate


def pick(order, lot, quantity, justification="", location=None):
    line = order.lines.get(article=lot.article)
    return {
        "order_line": line,
        "lot": lot,
        "location": location or lot.location,
        "quantity": Decimal(quantity),
        "justification": justification,
    }


# --- DLC minimale client (règle 5, à la date de livraison) ------------------------------


def test_dlc_minimale_calculee_a_la_date_de_livraison(
    private_label_customer, brand_only_customer, finished_product
):
    delivery = TODAY() + timedelta(days=3)
    # 14 j × 70 % = 9,8 jours restants → DLC au moins à livraison + 10 jours
    assert shipping.min_expiry_for(
        private_label_customer, finished_product, delivery
    ) == delivery + timedelta(days=10)
    # 14 j × 75 % = 10,5 jours → livraison + 11 jours
    assert shipping.min_expiry_for(
        brand_only_customer, finished_product, delivery
    ) == delivery + timedelta(days=11)


def test_la_proposition_fefo_exclut_les_lots_trop_courts(make_order, finished_product, stock):
    order = make_order([(finished_product, "600")])
    (row,) = shipping.picking_proposal(order)
    assert row["min_expiry_date"] == TODAY() + timedelta(days=12)
    assert [(item.lot, item.suggested) for item in row["lots"]] == [
        (stock["premier"], Decimal("300")),
        (stock["second"], Decimal("300")),
    ]
    assert [item.lot for item in row["too_short"]] == [stock["court"]]
    assert row["missing"] == 0


def test_la_proposition_signale_le_manquant(make_order, finished_product, stock):
    order = make_order([(finished_product, "1500")])
    (row,) = shipping.picking_proposal(order)
    assert row["missing"] == Decimal("200")


def test_un_lot_trop_court_pour_l_enseigne_est_refuse(make_order, finished_product, stock):
    order = make_order([(finished_product, "100")])
    with pytest.raises(ValidationError, match="trop court pour ENS2"):
        shipping.prepare_order(
            order, lines=[pick(order, stock["court"], "100", justification="Plus proche du quai")]
        )


def test_la_dlc_minimale_depend_de_la_date_de_livraison(make_order, finished_product, stock):
    """Livré à J+3, le lot à J+12 devient trop court (il faut une DLC à J+13)."""
    order = make_order([(finished_product, "100")], days=3)
    (row,) = shipping.picking_proposal(order)
    assert [item.lot for item in row["lots"]] == [stock["second"]]
    with pytest.raises(ValidationError, match="trop court"):
        shipping.prepare_order(order, lines=[pick(order, stock["premier"], "100", "Test")])


# --- Préparation ------------------------------------------------------------------


def test_preparer_en_fefo_ne_cree_aucun_mouvement(make_order, finished_product, stock, make_user):
    order = make_order([(finished_product, "400")])
    movements_before = StockMovement.objects.count()
    shipment = shipping.prepare_order(
        order,
        lines=[pick(order, stock["premier"], "300"), pick(order, stock["second"], "100")],
        user=make_user("magasinier"),
    )
    order.refresh_from_db()
    assert order.status == OrderStatus.PREPARING
    assert shipment.number.startswith(f"BL-{TODAY().year}-")
    assert shipment.status == ShipmentStatus.PREPARED
    assert shipment.lines.count() == 2
    assert StockMovement.objects.count() == movements_before


def test_un_lot_hors_fefo_exige_une_justification(make_order, finished_product, stock):
    order = make_order([(finished_product, "200")])
    with pytest.raises(ValidationError, match="hors FEFO"):
        shipping.prepare_order(order, lines=[pick(order, stock["second"], "200")])

    shipment = shipping.prepare_order(
        order, lines=[pick(order, stock["second"], "200", "Palette déjà filmée au quai")]
    )
    assert shipment.lines.get().fefo_justification == "Palette déjà filmée au quai"


def test_on_ne_prepare_pas_plus_que_la_quantite_commandee(make_order, finished_product, stock):
    order = make_order([(finished_product, "100")])
    with pytest.raises(ValidationError, match="préparés pour 100 commandés"):
        shipping.prepare_order(order, lines=[pick(order, stock["premier"], "150")])


def test_on_ne_prepare_pas_plus_que_le_stock(make_order, finished_product, stock):
    order = make_order([(finished_product, "600")])
    with pytest.raises(ValidationError, match="300 u disponibles"):
        shipping.prepare_order(order, lines=[pick(order, stock["premier"], "400")])


def test_une_preparation_vide_est_refusee(make_order, finished_product, stock):
    order = make_order([(finished_product, "100")])
    with pytest.raises(ValidationError, match="rien à expédier"):
        shipping.prepare_order(order, lines=[pick(order, stock["premier"], "0")])


def test_seul_un_lot_libere_se_prepare(make_order, finished_product, stock):
    stock_services.block_lot(stock["premier"], reason="Analyse en cours")
    order = make_order([(finished_product, "100")])
    with pytest.raises(ValidationError, match="seul un lot libéré"):
        shipping.prepare_order(order, lines=[pick(order, stock["premier"], "100", "Test")])


def test_deux_preparations_ne_prennent_pas_le_meme_stock(make_order, finished_product, stock):
    first = make_order([(finished_product, "300")])
    shipping.prepare_order(first, lines=[pick(first, stock["premier"], "300")])

    second = make_order([(finished_product, "100")])
    (row,) = shipping.picking_proposal(second)
    assert [item.lot for item in row["lots"]] == [stock["second"]]
    with pytest.raises(ValidationError, match="hors préparations en cours"):
        shipping.prepare_order(second, lines=[pick(second, stock["premier"], "100", "Test")])


def test_une_commande_ne_se_prepare_qu_une_fois(make_order, finished_product, stock):
    order = make_order([(finished_product, "100")])
    shipping.prepare_order(order, lines=[pick(order, stock["premier"], "100")])
    with pytest.raises(ValidationError, match="seule une commande reçue"):
        shipping.prepare_order(order, lines=[pick(order, stock["premier"], "100")])


def test_annuler_la_preparation_libere_la_commande(make_order, finished_product, stock):
    order = make_order([(finished_product, "100")])
    shipment = shipping.prepare_order(order, lines=[pick(order, stock["premier"], "100")])
    with pytest.raises(ValidationError):
        shipping.cancel_preparation(shipment, reason=" ")
    shipping.cancel_preparation(shipment, reason="Erreur de lot")
    order.refresh_from_db()
    shipment.refresh_from_db()
    assert order.status == OrderStatus.RECEIVED
    assert shipment.status == ShipmentStatus.CANCELLED
    # La commande peut être préparée de nouveau
    shipping.prepare_order(order, lines=[pick(order, stock["premier"], "100")])


# --- Expédition -------------------------------------------------------------------


def test_expedier_cree_les_mouvements_relies_a_l_enseigne(
    make_order, finished_product, stock, warehouses
):
    order = make_order([(finished_product, "400")])
    shipment = shipping.prepare_order(
        order, lines=[pick(order, stock["premier"], "300"), pick(order, stock["second"], "100")]
    )
    shipment = shipping.ship_order(shipment, carrier="Transports Bretagne Froid", temperature=3)

    order.refresh_from_db()
    assert shipment.status == ShipmentStatus.SHIPPED
    assert order.status == OrderStatus.SHIPPED
    movements = StockMovement.objects.filter(movement_type=MovementType.SHIPMENT)
    assert {(m.lot, -m.quantity) for m in movements} == {
        (stock["premier"], Decimal("300")),
        (stock["second"], Decimal("100")),
    }
    assert {m.reference for m in movements} == {shipment.number}
    assert {m.customer_warehouse for m in movements} == {warehouses["ENS2-E01"]}
    assert stock["premier"].quantity == 0
    # Traçabilité aval (règle 1) : le lot mène à l'entrepôt livré
    (delivery,) = downstream(stock["second"]).shipments
    assert delivery["warehouse"] == warehouses["ENS2-E01"]
    assert delivery["quantity"] == Decimal("100")


def test_la_rupture_n_est_pas_un_reliquat(make_order, finished_product, mdd_lasagna, stock):
    """Ce qui manque n'est pas livré plus tard : la commande est soldée à l'expédition."""
    order = make_order([(finished_product, "400"), (mdd_lasagna, "120")])
    shipment = shipping.prepare_order(order, lines=[pick(order, stock["premier"], "300")])
    shipping.ship_order(shipment, carrier="TBF", temperature=Decimal("2.5"))
    order.refresh_from_db()
    assert order.status == OrderStatus.SHIPPED
    with pytest.raises(ValidationError):
        shipping.prepare_order(order, lines=[pick(order, stock["second"], "100", "Reliquat")])


def test_transporteur_et_temperature_obligatoires(make_order, finished_product, stock):
    order = make_order([(finished_product, "100")])
    shipment = shipping.prepare_order(order, lines=[pick(order, stock["premier"], "100")])
    with pytest.raises(ValidationError) as exc:
        shipping.ship_order(shipment, carrier="", temperature=None)
    assert set(exc.value.message_dict) == {"carrier", "temperature"}


def test_au_dessus_de_4_degres_l_expedition_est_refusee(make_order, finished_product, stock):
    order = make_order([(finished_product, "400")])
    shipment = shipping.prepare_order(
        order, lines=[pick(order, stock["premier"], "300"), pick(order, stock["second"], "100")]
    )
    shipment = shipping.ship_order(shipment, carrier="TBF", temperature=Decimal("5.8"))

    order.refresh_from_db()
    assert shipment.status == ShipmentStatus.REFUSED
    assert "5,8 °C" in shipment.refusal_reason
    # Aucun mouvement d'expédition, lots préparés bloqués, alerte critique
    assert not StockMovement.objects.filter(movement_type=MovementType.SHIPMENT).exists()
    for lot in (stock["premier"], stock["second"]):
        lot.refresh_from_db()
        assert lot.status == LotStatus.BLOCKED
        assert "5,8 °C" in lot.block_reason
    alert = Alert.objects.get(alert_type=AlertType.SHIPPING_TEMPERATURE)
    assert alert.level == "critique"
    assert shipment.number in alert.message
    # La commande redevient « reçue » : on peut la préparer avec d'autres lots
    assert order.status == OrderStatus.RECEIVED


def test_a_4_degres_l_expedition_passe(make_order, finished_product, stock):
    order = make_order([(finished_product, "100")])
    shipment = shipping.prepare_order(order, lines=[pick(order, stock["premier"], "100")])
    assert shipping.ship_order(shipment, carrier="TBF", temperature=4).status == "expediee"


def test_le_stock_est_recontrole_a_l_expedition(make_order, finished_product, stock):
    order = make_order([(finished_product, "100")])
    shipment = shipping.prepare_order(order, lines=[pick(order, stock["premier"], "100")])
    stock_services.block_lot(stock["premier"], reason="Rappel fournisseur")
    with pytest.raises(ValidationError, match="Annule la préparation"):
        shipping.ship_order(shipment, carrier="TBF", temperature=3)


# --- Palettes et SSCC -------------------------------------------------------------


def test_cle_de_controle_gs1():
    # Exemple publié par GS1 pour un GTIN-13 : 400638133393 → clé 1 (même algorithme)
    assert shipping.gs1_check_digit("400638133393") == 1
    assert shipping.sscc_from_serial(1) == "037700000000000016"


def test_decoupage_en_palettes_de_720_unites(make_order, finished_product, make_pf_lot, platform):
    big = make_pf_lot(finished_product, "2000", 12)
    order = make_order([(finished_product, "1500")])
    shipment = shipping.prepare_order(order, lines=[pick(order, big, "1500")])
    shipment = shipping.ship_order(shipment, carrier="TBF", temperature=3)

    pallets = list(shipment.pallets.all())
    assert [p.total_quantity for p in pallets] == [Decimal("720"), Decimal("720"), Decimal("60")]
    assert [p.rank for p in pallets] == [1, 2, 3]
    for pallet in pallets:
        assert len(pallet.sscc) == 18 and pallet.sscc.isdigit()
        assert pallet.sscc.startswith("03770000")
        assert int(pallet.sscc[-1]) == shipping.gs1_check_digit(pallet.sscc[:-1])
    assert len({p.sscc for p in pallets}) == 3


# --- Taux de service --------------------------------------------------------------


def _ship(order, lot, quantity):
    shipment = shipping.prepare_order(order, lines=[pick(order, lot, quantity)])
    return shipping.ship_order(shipment, carrier="TBF", temperature=3)


def test_taux_de_service_complet_partiel_en_retard(
    make_order, finished_product, make_pf_lot, private_label_customer
):
    lot = make_pf_lot(finished_product, "5000", 20)
    complete = make_order([(finished_product, "100")], days=2)
    _ship(complete, lot, "100")
    partial = make_order([(finished_product, "100")], days=2)
    _ship(partial, lot, "60")
    late = make_order([(finished_product, "100")], days=1)
    _ship(late, lot, "100")
    # Expédiée le jour même de la livraison demandée (au lieu de la veille) : en retard
    Shipment.objects.filter(order=late).update(shipped_at=timezone.now() + timedelta(days=1))
    pending = make_order([(finished_product, "100")], days=3)  # encore dans les temps
    cancelled = make_order([(finished_product, "100")], days=2)
    orders.cancel_order(cancelled)

    report = shipping.service_rate(start=TODAY(), end=TODAY() + timedelta(days=5))
    (row,) = report["customers"]
    assert row["customer"] == private_label_customer
    assert row["ordered"] == Decimal("300")  # ni la commande en cours, ni l'annulée
    assert row["on_time"] == Decimal("160")
    assert row["late"] == Decimal("100")
    assert row["missing"] == Decimal("40")
    assert row["rate"] == Decimal("53.3")
    assert row["below_target"] is True
    assert row["perfect_orders"] == 1
    assert row["pending_orders"] == 1
    assert {issue["order"]: issue["problem"] for issue in report["issues"]} == {
        partial: "incomplète (rupture)",
        late: "en retard",
    }
    assert pending.status == OrderStatus.RECEIVED


def test_une_commande_non_expediee_a_temps_compte_comme_non_livree(make_order, finished_product):
    order = make_order([(finished_product, "100")], days=2)
    report = shipping.service_rate(
        start=TODAY(), end=TODAY() + timedelta(days=5), today=TODAY() + timedelta(days=2)
    )
    assert report["total"]["rate"] == Decimal("0.0")
    assert report["issues"][0]["order"] == order
    assert report["issues"][0]["problem"] == "non expédiée"


def test_taux_de_service_a_100_pour_cent(make_order, finished_product, make_pf_lot):
    lot = make_pf_lot(finished_product, "500", 20)
    _ship(make_order([(finished_product, "100")]), lot, "100")
    report = shipping.service_rate(start=TODAY(), end=TODAY() + timedelta(days=5))
    assert report["total"]["rate"] == Decimal("100.0")
    assert report["total"]["below_target"] is False
