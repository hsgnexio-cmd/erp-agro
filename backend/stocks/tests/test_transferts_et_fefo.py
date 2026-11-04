"""Transferts, corrections (règle 11) et FEFO (règle 4)."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from stocks import services
from stocks.choices import MovementType
from stocks.tests.conftest import make_location

# --- Transferts ---------------------------------------------------------------


def test_un_lot_peut_etre_reparti_sur_plusieurs_emplacements(
    make_lot, cream, cold_room, factory_cold_room
):
    lot = services.release_lot(make_lot(cream, "400"))
    services.transfer(
        lot, from_location=lot.location, to_location=cold_room, quantity=Decimal("400")
    )
    number = services.transfer(
        lot, from_location=cold_room, to_location=factory_cold_room, quantity=Decimal("150")
    )

    stock = {location.code: quantity for location, quantity in services.stock_by_location(lot)}
    assert stock == {"MPE-FP-01": Decimal("250"), "NAN-CF-MP": Decimal("150")}
    assert lot.quantity == Decimal("400")  # un transfert ne change pas la quantité totale
    pair = lot.movements.filter(reference=number)
    assert {m.movement_type for m in pair} == {MovementType.TRANSFER_OUT, MovementType.TRANSFER_IN}


def test_pas_de_transfert_au_dela_du_stock(make_lot, cream, cold_room):
    lot = make_lot(cream, "100")
    with pytest.raises(ValidationError) as exc:
        services.transfer(
            lot, from_location=lot.location, to_location=cold_room, quantity=Decimal("101")
        )
    assert "Stock insuffisant" in exc.value.message_dict["quantity"][0]


def test_un_lot_en_quarantaine_peut_etre_range(make_lot, cream, cold_room):
    lot = make_lot(cream)
    services.transfer(
        lot, from_location=lot.location, to_location=cold_room, quantity=Decimal("10")
    )


def test_le_frais_ne_va_pas_en_ambiant(make_lot, cream, ambient_store):
    lot = make_lot(cream)
    with pytest.raises(ValidationError) as exc:
        services.transfer(
            lot, from_location=lot.location, to_location=ambient_store, quantity=Decimal("10")
        )
    assert exc.value.message_dict["location"][0] == (
        "MP-LAI-CREME35 se conserve en « Froid positif (0 à 4 °C) » : "
        "l'emplacement MPE-AMB-01 est en « Ambiant »."
    )


def test_un_lot_detruit_ne_se_deplace_plus(make_lot, cream, cold_room):
    lot = services.destroy_lot(services.block_lot(make_lot(cream), reason="X"), reason="Y")
    with pytest.raises(ValidationError):
        services.transfer(
            lot, from_location=lot.location, to_location=cold_room, quantity=Decimal("1")
        )


def test_meme_emplacement_refuse(make_lot, cream):
    lot = make_lot(cream)
    with pytest.raises(ValidationError):
        services.transfer(
            lot, from_location=lot.location, to_location=lot.location, quantity=Decimal("1")
        )


# --- Corrections --------------------------------------------------------------


def test_correction_partielle_d_une_reception(make_lot, cream):
    """400 kg saisis au lieu de 40 kg : on corrige 360 kg, sans toucher à l'original."""
    lot = make_lot(cream, "400")
    reception = lot.movements.get()
    correction = services.correct_movement(
        reception, quantity=Decimal("360"), reason="Erreur de saisie : 40 kg livrés"
    )

    assert correction.quantity == Decimal("-360")
    assert correction.corrected_movement == reception
    assert lot.quantity == Decimal("40")
    reception.refresh_from_db()
    assert reception.quantity == Decimal("400")


def test_on_ne_corrige_pas_plus_que_le_mouvement(make_lot, cream):
    lot = make_lot(cream, "100")
    reception = lot.movements.get()
    services.correct_movement(reception, quantity=Decimal("60"), reason="A")
    with pytest.raises(ValidationError):
        services.correct_movement(reception, quantity=Decimal("50"), reason="B")
    services.correct_movement(reception, reason="Annulation du reste")
    assert lot.quantity == 0


def test_la_correction_ne_rend_pas_le_stock_negatif(make_lot, cream, cold_room):
    lot = make_lot(cream, "100")
    services.transfer(
        lot, from_location=lot.location, to_location=cold_room, quantity=Decimal("80")
    )
    with pytest.raises(ValidationError) as exc:
        services.correct_movement(lot.movements.get(movement_type="reception"), reason="Erreur")
    assert "restent" in exc.value.message_dict["quantity"][0]


def test_un_transfert_ne_se_corrige_pas_par_une_correction(make_lot, cream, cold_room):
    lot = make_lot(cream, "100")
    services.transfer(
        lot, from_location=lot.location, to_location=cold_room, quantity=Decimal("10")
    )
    with pytest.raises(ValidationError):
        services.correct_movement(
            lot.movements.get(movement_type=MovementType.TRANSFER_IN), reason="Erreur"
        )


# --- FEFO -----------------------------------------------------------------------


@pytest.fixture
def three_cream_lots(make_lot, cream, cold_room):
    """Trois lots libérés de 100 kg, DLC dans 15, 5 et 10 jours."""
    lots = {}
    for days in (15, 5, 10):
        lot = services.release_lot(make_lot(cream, "100", expiry_in=days))
        services.transfer(
            lot, from_location=lot.location, to_location=cold_room, quantity=Decimal("100")
        )
        lots[days] = lot
    return lots


def test_fefo_propose_d_abord_le_lot_qui_perime_le_premier(three_cream_lots, cream, warehouse):
    plan = services.fefo_plan(cream, warehouse, Decimal("150"))

    assert [line.lot for line in plan.lines] == [three_cream_lots[5], three_cream_lots[10]]
    assert [line.take for line in plan.lines] == [Decimal("100"), Decimal("50")]
    assert plan.missing == 0


def test_fefo_ignore_les_lots_non_liberes(three_cream_lots, make_lot, cream, warehouse):
    make_lot(cream, "100", expiry_in=2)  # en quarantaine : pas proposé
    services.block_lot(three_cream_lots[5], reason="Analyse")
    plan = services.fefo_plan(cream, warehouse, Decimal("100"))
    assert [line.lot for line in plan.lines] == [three_cream_lots[10]]


def test_fefo_ignore_les_lots_perimes(three_cream_lots, cream, warehouse):
    from datetime import timedelta

    from django.utils import timezone

    in_7_days = timezone.localdate() + timedelta(days=7)
    plan = services.fefo_plan(cream, warehouse, Decimal("100"), on_date=in_7_days)
    assert three_cream_lots[5] not in [line.lot for line in plan.lines]


def test_fefo_dlc_minimale_exigee(three_cream_lots, cream, warehouse):
    """Préparation de la règle 5 : un client exige au moins 12 jours de DLC."""
    from datetime import timedelta

    from django.utils import timezone

    minimum = timezone.localdate() + timedelta(days=12)
    plan = services.fefo_plan(cream, warehouse, Decimal("300"), min_expiry_date=minimum)
    assert [line.lot for line in plan.lines] == [three_cream_lots[15]]
    assert plan.missing == Decimal("200")


def test_fefo_par_site(three_cream_lots, cream, factory_site):
    make_location(factory_site, "NAN-CF-MP")
    plan = services.fefo_plan(cream, factory_site, Decimal("10"))
    assert plan.lines == []
    assert plan.missing == Decimal("10")


# --- État des stocks ------------------------------------------------------------


def test_etat_des_stocks_par_statut(three_cream_lots, make_lot, cream, warehouse):
    make_lot(cream, "40")  # quarantaine
    services.block_lot(three_cream_lots[15], reason="Analyse")
    rows = services.stock_summary(site=warehouse)

    assert rows == [
        {
            "article": cream.id,
            "article_code": "MP-LAI-CREME35",
            "article_name": "Crème 35 %",
            "unit": "kg",
            "site_code": "MPE",
            "released": Decimal("200"),
            "quarantine": Decimal("40"),
            "blocked": Decimal("100"),
            "total": Decimal("340"),
        }
    ]
