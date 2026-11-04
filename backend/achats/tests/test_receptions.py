"""Réceptions : contrôles, création des lots (règles 2, 6, 7) et des mouvements (règle 11)."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from achats.choices import PurchaseOrderStatus
from referentiel.choices import TemperatureClass
from referentiel.models import Location
from stocks.choices import LotStatus, MovementType
from stocks.models import Lot, StockMovement

TODAY = timezone.localdate


@pytest.fixture
def order(make_order, cream_at_supplier, cream):
    return make_order((cream, "100"))


def received_lot(reception) -> Lot:
    return reception.lines.get().lot


# --- Création du lot et du mouvement ------------------------------------------


def test_une_reception_conforme_cree_un_lot_en_quarantaine(order, receive):
    reception = receive(order, supplier_lot_number="CB-0412")
    lot = received_lot(reception)

    assert lot.status == LotStatus.QUARANTINE
    assert lot.number.startswith(f"LR-{TODAY():%y%m%d}-")
    assert lot.article.code == "MP-LAI-CREME35"
    assert lot.supplier.code == "FOU-004"
    assert lot.supplier_lot_number == "CB-0412"
    assert lot.date_type == "DLC"
    assert lot.expiry_date == TODAY() + timedelta(days=20)
    assert lot.location.code == "MPE-QUAR"
    assert lot.quantity == Decimal("100")
    assert reception.lines.get().is_compliant


def test_la_reception_cree_un_mouvement_d_entree(order, receive, make_user):
    reception = receive(order)
    movement = StockMovement.objects.get()

    assert movement.movement_type == MovementType.RECEPTION
    assert movement.quantity == Decimal("100")
    assert movement.reference == reception.number
    assert movement.lot == received_lot(reception)


def test_reception_partielle_puis_soldee(order, receive):
    receive(order, quantity="60")
    order.refresh_from_db()
    assert order.status == PurchaseOrderStatus.PARTIAL

    receive(order, quantity="40")
    order.refresh_from_db()
    assert order.status == PurchaseOrderStatus.CLOSED
    assert Lot.objects.count() == 2


def test_on_ne_receptionne_pas_un_brouillon(make_order, receive, cream_at_supplier, cream):
    draft = make_order((cream, "100"), send=False)
    with pytest.raises(ValidationError) as exc:
        receive(draft)
    assert "envoyée" in exc.value.messages[0]


def test_on_ne_receptionne_pas_une_commande_soldee(order, receive):
    receive(order)
    with pytest.raises(ValidationError):
        receive(order, quantity="5")


# --- Quantités ----------------------------------------------------------------


def test_livraison_superieure_acceptee_jusqu_a_10_pourcent(order, receive):
    receive(order, quantity="110")
    order.refresh_from_db()
    assert order.status == PurchaseOrderStatus.CLOSED


def test_livraison_superieure_a_10_pourcent_refusee(order, receive):
    with pytest.raises(ValidationError) as exc:
        receive(order, quantity="111")
    assert "+ 10 %" in exc.value.message_dict["lines"][0]
    # Rien n'est enregistré : ni lot, ni mouvement
    assert Lot.objects.count() == 0
    assert StockMovement.objects.count() == 0


# --- Saisies obligatoires -----------------------------------------------------


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("supplier_lot_number", "lot fournisseur"),
        ("expiry_date", "DLC est obligatoire"),
        ("temperature", "température est obligatoire"),
    ],
)
def test_saisies_obligatoires(order, receive, field, message):
    value = "" if field == "supplier_lot_number" else None
    with pytest.raises(ValidationError) as exc:
        receive(order, **{field: value})
    assert message in exc.value.message_dict["lines"][0]


def test_un_produit_sec_sans_temperature(make_order, receive, flour_at_supplier, flour):
    order = make_order((flour, "100"))
    lot = received_lot(receive(order, temperature=None, expiry_date=TODAY() + timedelta(days=300)))
    assert lot.status == LotStatus.QUARANTINE
    assert lot.date_type == "DDM"


def test_un_emballage_sans_date_ni_temperature(make_order, receive, supplier, tray):
    from achats.tests.conftest import reference

    reference(supplier, tray, price="0.085")
    order = make_order((tray, "5000"))
    lot = received_lot(receive(order, temperature=None, expiry_date=None))
    assert lot.status == LotStatus.QUARANTINE
    assert lot.expiry_date is None


# --- Contrôles à réception ----------------------------------------------------


def test_temperature_trop_haute_bloque_le_lot(order, receive):
    reception = receive(order, temperature="6.5")
    lot = received_lot(reception)

    assert lot.status == LotStatus.BLOCKED
    assert "6,5 °C" in lot.block_reason
    assert not reception.lines.get().is_compliant


def test_temperature_limite_acceptee(order, receive):
    assert received_lot(receive(order, temperature="4.0")).status == LotStatus.QUARANTINE


def test_surgele_au_dessus_de_moins_18_bloque(make_order, receive, supplier, peas):
    from achats.tests.conftest import reference

    reference(supplier, peas, price="1.70")
    order = make_order((peas, "100"))
    lot = received_lot(receive(order, temperature="-15", expiry_date=TODAY() + timedelta(days=500)))
    assert lot.status == LotStatus.BLOCKED


def test_produit_perime_bloque(order, receive):
    lot = received_lot(receive(order, expiry_date=TODAY()))
    assert lot.status == LotStatus.BLOCKED
    assert "périmé" in lot.block_reason


def test_duree_de_vie_restante_insuffisante(order, receive):
    """Crème : 21 jours de DLC, minimum 60 % à réception, soit 12,6 jours."""
    lot = received_lot(receive(order, quantity="50", expiry_date=TODAY() + timedelta(days=12)))
    assert lot.status == LotStatus.BLOCKED
    assert "57 %" in lot.block_reason

    order2_lot = received_lot(
        receive(order, quantity="5", expiry_date=TODAY() + timedelta(days=13))
    )
    assert order2_lot.status == LotStatus.QUARANTINE


def test_aspect_non_conforme_bloque(order, receive):
    lot = received_lot(receive(order, appearance_ok=False))
    assert lot.status == LotStatus.BLOCKED
    assert "Aspect" in lot.block_reason


def test_documents_non_conformes_bloquent_le_lot(order, receive):
    lot = received_lot(receive(order, documents_ok=False))
    assert lot.status == LotStatus.BLOCKED
    assert "Documents" in lot.block_reason


def test_plusieurs_motifs_sont_cumules(order, receive):
    lot = received_lot(receive(order, temperature="8", appearance_ok=False))
    assert "Température" in lot.block_reason
    assert "Aspect" in lot.block_reason


def test_l_emplacement_doit_etre_sur_le_site_de_livraison(order, cream, factory_site):
    from achats import services

    other = Location.objects.create(
        site=factory_site,
        code="NAN-CF-MP",
        name="Chambre froide",
        temperature_class=TemperatureClass.CHILLED,
    )
    with pytest.raises(ValidationError) as exc:
        services.create_reception(
            order=order,
            location=other,
            delivery_note_number="BL-1",
            lines=[
                {
                    "order_line": order.lines.get(),
                    "quantity": Decimal("10"),
                    "supplier_lot_number": "X",
                    "expiry_date": TODAY() + timedelta(days=20),
                    "temperature": Decimal("3"),
                }
            ],
        )
    assert "MPE" in exc.value.message_dict["location"][0]


def test_l_emplacement_de_depot_doit_etre_a_la_bonne_temperature(
    make_order, receive, quarantine_zones, cream_at_supplier, cream
):
    """Chaîne du froid : de la crème ne se dépose pas en zone ambiante."""
    order = make_order((cream, "100"))
    with pytest.raises(ValidationError) as exc:
        receive(order, location=quarantine_zones[TemperatureClass.AMBIENT])
    assert "« Froid positif (0 à 4 °C) »" in exc.value.message_dict["lines"][0]
    assert Lot.objects.count() == 0
