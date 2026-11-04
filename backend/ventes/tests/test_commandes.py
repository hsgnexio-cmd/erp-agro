"""Tarifs de vente et prise de commande."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from ventes import orders
from ventes.models import SalePrice
from ventes.tests.conftest import at

TODAY = timezone.localdate


def line(article, quantity="120"):
    return {"article": article, "quantity": Decimal(quantity)}


# --- Heure limite -----------------------------------------------------------------


def test_avant_11_h_livrable_des_le_lendemain():
    assert orders.earliest_delivery_date(at(10, 59)) == TODAY() + timedelta(days=1)


def test_apres_11_h_livrable_a_j_plus_2():
    assert orders.earliest_delivery_date(at(11, 0)) == TODAY() + timedelta(days=2)


def test_livraison_trop_tot_refusee(private_label_customer, warehouses, finished_product, prices):
    with pytest.raises(ValidationError) as exc:
        orders.create_order(
            customer=private_label_customer,
            warehouse=warehouses["ENS2-E01"],
            requested_delivery_date=TODAY() + timedelta(days=1),
            lines=[line(finished_product)],
            received_at=at(14, 0),
        )
    assert "heure limite 11 h" in exc.value.messages[0]


# --- Produits commandables (règle 10) -------------------------------------------------


def test_un_produit_mdd_n_est_commandable_que_par_son_enseigne(
    brand_only_customer, warehouses, mdd_lasagna, prices
):
    with pytest.raises(ValidationError) as exc:
        orders.create_order(
            customer=brand_only_customer,
            warehouse=warehouses["ENS4-E01"],
            requested_delivery_date=TODAY() + timedelta(days=2),
            lines=[line(mdd_lasagna)],
        )
    assert "MDD de ENS2" in exc.value.messages[0]


def test_produits_commandables_par_enseigne(
    private_label_customer, brand_only_customer, finished_product, mdd_lasagna, prices
):
    for_ens2 = {
        row["article"] for row in orders.orderable_articles(private_label_customer, TODAY())
    }
    for_ens4 = {row["article"] for row in orders.orderable_articles(brand_only_customer, TODAY())}
    assert for_ens2 == {finished_product, mdd_lasagna}
    assert for_ens4 == {finished_product}


def test_l_entrepot_doit_appartenir_a_l_enseigne(
    private_label_customer, warehouses, finished_product, prices
):
    with pytest.raises(ValidationError) as exc:
        orders.create_order(
            customer=private_label_customer,
            warehouse=warehouses["ENS4-E01"],
            requested_delivery_date=TODAY() + timedelta(days=2),
            lines=[line(finished_product)],
        )
    assert "n'appartient pas" in exc.value.messages[0]


# --- Création et prix ---------------------------------------------------------------


def test_creation_d_une_commande_valorisee(
    private_label_customer, warehouses, finished_product, mdd_lasagna, prices
):
    order = orders.create_order(
        customer=private_label_customer,
        warehouse=warehouses["ENS2-E01"],
        requested_delivery_date=TODAY() + timedelta(days=2),
        lines=[line(finished_product, "240"), line(mdd_lasagna, "120")],
        customer_reference="MP-1234",
    )
    assert order.number.startswith("CC-")
    assert order.status == "recue"
    assert order.total_amount == Decimal("742.80")  # 240 × 2,15 + 120 × 1,89


def test_une_ligne_sans_tarif_est_acceptee_mais_a_valoriser(
    brand_only_customer, warehouses, finished_product
):
    order = orders.create_order(
        customer=brand_only_customer,
        warehouse=warehouses["ENS4-E01"],
        requested_delivery_date=TODAY() + timedelta(days=2),
        lines=[line(finished_product)],
    )
    assert order.lines.get().unit_price is None


def test_quantites_et_doublons(private_label_customer, warehouses, finished_product, prices):
    with pytest.raises(ValidationError) as exc:
        orders.create_order(
            customer=private_label_customer,
            warehouse=warehouses["ENS2-E01"],
            requested_delivery_date=TODAY() + timedelta(days=2),
            lines=[line(finished_product, "0"), line(finished_product, "12")],
        )
    messages = " ".join(exc.value.messages)
    assert "deux fois" in messages and "au moins 1" in messages


def test_annulation(private_label_customer, warehouses, finished_product, prices):
    order = orders.create_order(
        customer=private_label_customer,
        warehouse=warehouses["ENS2-E01"],
        requested_delivery_date=TODAY() + timedelta(days=2),
        lines=[line(finished_product)],
    )
    assert orders.cancel_order(order).status == "annulee"
    with pytest.raises(ValidationError):
        orders.cancel_order(order)


# --- Tarifs de vente ----------------------------------------------------------------


def test_deux_tarifs_ne_se_chevauchent_pas(private_label_customer, finished_product, prices):
    with pytest.raises(ValidationError):
        SalePrice.objects.create(
            customer=private_label_customer,
            article=finished_product,
            unit_price=Decimal("2.30"),
            valid_from=TODAY(),
        )


def test_pas_de_tarif_mdd_pour_une_autre_enseigne(brand_only_customer, mdd_lasagna):
    with pytest.raises(ValidationError) as exc:
        SalePrice.objects.create(
            customer=brand_only_customer,
            article=mdd_lasagna,
            unit_price=Decimal("1.90"),
            valid_from=TODAY(),
        )
    assert "MDD" in exc.value.message_dict["article"][0]
