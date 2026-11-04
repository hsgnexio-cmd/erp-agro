"""Règle 6 : statuts des lots (libéré, bloqué, quarantaine, détruit)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from stocks import services
from stocks.choices import LotStatus, MovementType
from stocks.models import Lot


def test_liberer_un_lot_en_quarantaine(make_lot, cream, make_user):
    lot = make_lot(cream)
    user = make_user("qualite")
    lot = services.release_lot(lot, user=user)

    assert lot.status == LotStatus.RELEASED
    change = lot.status_changes.get()
    assert (change.from_status, change.to_status) == ("quarantaine", "libere")
    assert change.user == user


def test_on_ne_libere_pas_un_lot_perime(make_lot, cream):
    lot = make_lot(cream)
    Lot.objects.filter(pk=lot.pk)  # la DLC est passée hier :
    lot.expiry_date = date.today() - timedelta(days=1)
    lot.save()
    with pytest.raises(ValidationError) as exc:
        services.release_lot(lot)
    assert "périmé" in exc.value.messages[0]


def test_un_lot_peut_etre_utilise_le_jour_de_sa_dlc(make_lot, cream):
    lot = make_lot(cream, expiry_in=0)
    assert services.release_lot(lot).status == LotStatus.RELEASED


def test_bloquer_exige_un_motif(make_lot, cream):
    lot = make_lot(cream)
    with pytest.raises(ValidationError) as exc:
        services.block_lot(lot, reason="  ")
    assert "reason" in exc.value.message_dict

    lot = services.block_lot(lot, reason="Suspicion de contamination")
    assert lot.status == LotStatus.BLOCKED
    assert lot.block_reason == "Suspicion de contamination"


def test_debloquer_exige_un_motif_et_efface_le_motif_de_blocage(make_lot, cream):
    lot = services.block_lot(make_lot(cream), reason="Analyse en cours")
    with pytest.raises(ValidationError):
        services.release_lot(lot)
    lot = services.release_lot(lot, reason="Analyse conforme")
    assert lot.status == LotStatus.RELEASED
    assert lot.block_reason == ""


@pytest.mark.parametrize(
    ("start", "target"),
    [
        ("quarantaine", "detruit"),  # on bloque d'abord, puis on détruit
        ("libere", "quarantaine"),  # on ne revient pas en quarantaine
        ("libere", "detruit"),
    ],
)
def test_passages_interdits(make_lot, cream, start, target):
    lot = make_lot(cream)
    if start == "libere":
        lot = services.release_lot(lot)
    with pytest.raises(ValidationError) as exc:
        services.change_status(lot, target, reason="Test")
    assert "Passage impossible" in exc.value.messages[0]


def test_detruire_sort_tout_le_stock(make_lot, cream, cold_room):
    lot = services.release_lot(make_lot(cream, "100"))
    services.transfer(
        lot, from_location=lot.location, to_location=cold_room, quantity=Decimal("30")
    )
    lot = services.block_lot(lot, reason="Contamination confirmée")
    lot = services.destroy_lot(lot, reason="Destruction après analyse")

    assert lot.status == LotStatus.DESTROYED
    assert lot.quantity == 0
    destructions = lot.movements.filter(movement_type=MovementType.DESTRUCTION)
    assert sorted(m.quantity for m in destructions) == [Decimal("-70"), Decimal("-30")]


def test_un_lot_detruit_ne_change_plus(make_lot, cream):
    lot = services.block_lot(make_lot(cream), reason="X")
    lot = services.destroy_lot(lot, reason="Y")
    with pytest.raises(ValidationError):
        services.release_lot(lot, reason="Erreur")


def test_le_journal_des_statuts_ne_se_modifie_pas(make_lot, cream):
    lot = services.release_lot(make_lot(cream))
    change = lot.status_changes.get()
    change.reason = "falsifié"
    with pytest.raises(ValidationError):
        change.save()


def test_calcul_de_la_dlc_d_un_produit_fini(finished_product):
    """Règle 3 : DLC = date de fabrication + durée de vie (14 jours pour les lasagnes)."""
    assert services.compute_expiry_date(finished_product, date(2026, 11, 4)) == date(2026, 11, 18)
