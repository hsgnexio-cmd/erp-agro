"""Règles sur les tarifs et les commandes fournisseurs."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from achats import services
from achats.choices import PurchaseOrderStatus
from achats.models import SupplierPrice
from achats.tests.conftest import reference
from referentiel.models import Supplier

# --- Tarifs -----------------------------------------------------------------


def test_deux_tarifs_ne_se_chevauchent_pas(cream_at_supplier):
    with pytest.raises(ValidationError):
        SupplierPrice.objects.create(
            supplier_article=cream_at_supplier,
            unit_price=Decimal("4.50"),
            valid_from=timezone.localdate(),
        )


def test_le_tarif_en_vigueur_depend_de_la_date(cream_at_supplier):
    today = timezone.localdate()
    old = cream_at_supplier.prices.get()
    old.valid_to = today - timedelta(days=1)
    old.save()
    SupplierPrice.objects.create(
        supplier_article=cream_at_supplier, unit_price=Decimal("4.50"), valid_from=today
    )

    assert services.current_price(cream_at_supplier, today).unit_price == Decimal("4.50")
    yesterday = today - timedelta(days=1)
    assert services.current_price(cream_at_supplier, yesterday).unit_price == Decimal("4.20")


# --- Création -----------------------------------------------------------------


def test_creation_d_une_commande(make_order, cream_at_supplier, cream):
    order = make_order((cream, "100"), send=False)

    year = timezone.localdate().year
    assert order.number == f"CA-{year}-00001"
    assert order.status == PurchaseOrderStatus.DRAFT
    line = order.lines.get()
    assert line.unit == "kg"
    assert line.unit_price == Decimal("4.2000")  # tarif en vigueur
    assert order.total_amount == Decimal("420.00")
    # Livraison prévue = date de commande + délai du fournisseur (3 jours)
    assert order.expected_delivery_date == order.order_date + timedelta(days=3)


def test_les_numeros_se_suivent(make_order, cream_at_supplier, cream):
    first = make_order((cream, "100"), send=False)
    second = make_order((cream, "100"), send=False)
    assert int(second.number[-5:]) == int(first.number[-5:]) + 1


def test_pas_de_commande_a_un_fournisseur_non_audite(make_order, cream):
    not_audited = Supplier.objects.create(code="FOU-007", name="Non audité", lead_time_days=2)
    reference(not_audited, cream)
    with pytest.raises(ValidationError) as exc:
        make_order((cream, "100"), supplier=not_audited, send=False)
    assert "pas audité" in exc.value.message_dict["supplier"][0]


def test_l_article_doit_etre_reference_chez_le_fournisseur(make_order, flour):
    with pytest.raises(ValidationError) as exc:
        make_order((flour, "100"), send=False)
    assert exc.value.message_dict["lines"][0] == (
        "MP-SEC-FARINE : article non référencé chez Crèmerie Bretonne."
    )


def test_quantite_minimale_de_commande(make_order, supplier, tray):
    reference(supplier, tray, price="0.085", minimum=Decimal("1000"))
    with pytest.raises(ValidationError) as exc:
        make_order((tray, "500"), send=False)
    assert "minimale" in exc.value.message_dict["lines"][0]
    make_order((tray, "1000"), send=False)


def test_sans_tarif_il_faut_saisir_le_prix(make_order, supplier, flour, warehouse):
    from referentiel.models import SupplierArticle

    SupplierArticle.objects.create(supplier=supplier, article=flour)
    with pytest.raises(ValidationError) as exc:
        make_order((flour, "100"), send=False)
    assert "Aucun tarif" in exc.value.message_dict["lines"][0]

    order = services.create_purchase_order(
        supplier=supplier,
        delivery_site=warehouse,
        lines=[{"article": flour, "quantity": Decimal("100"), "unit_price": Decimal("0.70")}],
    )
    assert order.lines.get().unit_price == Decimal("0.70")


def test_une_commande_a_au_moins_une_ligne(make_order):
    with pytest.raises(ValidationError):
        make_order(send=False)


# --- Statuts ------------------------------------------------------------------


def test_envoi_d_une_commande(make_order, cream_at_supplier, cream):
    order = make_order((cream, "100"))
    assert order.status == PurchaseOrderStatus.SENT
    assert order.sent_at is not None


def test_une_commande_envoyee_n_est_plus_modifiable(make_order, cream_at_supplier, cream):
    order = make_order((cream, "100"))
    with pytest.raises(ValidationError):
        services.update_purchase_order(order, comment="modification")
    with pytest.raises(ValidationError):
        line = order.lines.get()
        line.quantity = Decimal("200")
        line.save()


def test_modification_d_un_brouillon(
    make_order, cream_at_supplier, cream, flour_at_supplier, flour
):
    order = make_order((cream, "100"), send=False)
    services.update_purchase_order(
        order, lines=[{"article": flour, "quantity": Decimal("250")}], comment="Farine finalement"
    )
    assert [line.article.code for line in order.lines.all()] == ["MP-SEC-FARINE"]
    assert order.comment == "Farine finalement"


def test_annulation(make_order, cream_at_supplier, cream):
    order = make_order((cream, "100"))
    services.cancel_order(order)
    assert order.status == PurchaseOrderStatus.CANCELLED
    with pytest.raises(ValidationError):
        services.send_order(order)


def test_pas_d_annulation_apres_reception(make_order, receive, cream_at_supplier, cream):
    order = make_order((cream, "100"))
    receive(order, quantity="40")
    with pytest.raises(ValidationError) as exc:
        services.cancel_order(order)
    assert "ne peut pas être annulée" in exc.value.messages[0]
