"""Sortie des invendables : don, alimentation animale, destruction (partie 7b)."""

import pytest
from django.core.exceptions import ValidationError

from stocks import services
from stocks.choices import LotStatus, MovementType


@pytest.fixture
def blocked_pf(make_lot, finished_product, cold_room):
    lot = services.release_lot(make_lot(finished_product, "240", location=cold_room))
    return services.block_lot(lot, reason="Barquettes mal scellées")


def test_un_invendable_bloque_part_en_don(blocked_pf, make_user):
    lot = services.dispose_unsold(
        blocked_pf, destination="don", reason="Banque alimentaire de Nantes", user=make_user()
    )
    assert lot.status == LotStatus.DESTROYED
    assert lot.quantity == 0
    (movement,) = lot.movements.filter(quantity__lt=0)
    assert movement.movement_type == MovementType.DONATION
    assert movement.quantity == -240
    assert movement.reason.startswith("Invendable – Don à une association")
    assert lot.status_changes.order_by("changed_at", "id").last().to_status == LotStatus.DESTROYED


@pytest.mark.parametrize(
    ("destination", "movement_type"),
    [
        ("alimentation_animale", MovementType.ANIMAL_FEED),
        ("destruction", MovementType.UNSOLD_DESTRUCTION),
    ],
)
def test_chaque_destination_a_son_mouvement(blocked_pf, destination, movement_type):
    lot = services.dispose_unsold(blocked_pf, destination=destination, reason="DLC courte")
    assert lot.movements.filter(movement_type=movement_type).exists()


def test_destination_et_motif_obligatoires(blocked_pf):
    with pytest.raises(ValidationError, match="destination"):
        services.dispose_unsold(blocked_pf, destination="", reason="X")
    with pytest.raises(ValidationError, match="motif"):
        services.dispose_unsold(blocked_pf, destination="don", reason="  ")


def test_un_lot_libere_dans_sa_date_ne_sort_pas_en_invendable(
    make_lot, finished_product, cold_room
):
    lot = services.release_lot(make_lot(finished_product, "100", location=cold_room))
    with pytest.raises(ValidationError, match="seul un lot bloqué ou périmé"):
        services.dispose_unsold(lot, destination="don", reason="Surstock")


def test_un_lot_perime_est_bloque_puis_sorti(make_lot, finished_product, cold_room):
    lot = services.release_lot(make_lot(finished_product, "100", location=cold_room))
    lot.expiry_date = lot.reception_date.replace(year=lot.reception_date.year - 1)
    lot.save()
    lot = services.dispose_unsold(lot, destination="destruction", reason="DLC dépassée")
    assert lot.status == LotStatus.DESTROYED
    assert [c.to_status for c in lot.status_changes.order_by("changed_at", "id")] == [
        LotStatus.RELEASED,
        LotStatus.BLOCKED,
        LotStatus.DESTROYED,
    ]


def test_seuls_les_produits_finis_sortent_en_invendable(make_lot, cream):
    lot = services.block_lot(make_lot(cream, "50"), reason="Odeur")
    with pytest.raises(ValidationError, match="n'est pas un produit fini"):
        services.dispose_unsold(lot, destination="destruction", reason="Odeur")


@pytest.mark.parametrize(("role", "expected"), [("qualite", 200), ("magasinier", 403)])
def test_seule_la_qualite_sort_un_invendable(api_client_for, blocked_pf, role, expected):
    response = api_client_for(role).post(
        f"/api/stocks/lots/{blocked_pf.id}/dispose/",
        {"destination": "alimentation_animale", "reason": "Ferme du Pont"},
        format="json",
    )
    assert response.status_code == expected
    if expected == 200:
        assert response.json()["status"] == LotStatus.DESTROYED
