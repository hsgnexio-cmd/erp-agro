"""Traçabilité (règle 1), rappel produit (règle 9) et allergènes (règle 8)."""

import time
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command

from qualite import services
from qualite.models import ProductRecall
from referentiel.models import Allergen
from stocks.choices import LotStatus
from stocks.models import Lot


def numbers(node) -> set[str]:
    """Tous les numéros de lot d'un arbre de traçabilité."""
    return {node.lot.number} | {n for child in node.children for n in numbers(child)}


# --- Traçabilité --------------------------------------------------------------


def test_tracabilite_amont_jusqu_aux_matieres_et_emballages(chain):
    tree = services.upstream(chain["lasagna"])
    assert numbers(tree) == {
        chain["lasagna"].number,
        chain["bechamel"].number,
        chain["cream_a"].number,
        chain["cream_b"].number,
        chain["trays"].number,
    }
    bechamel = next(c for c in tree.children if c.lot == chain["bechamel"])
    assert bechamel.quantity == Decimal("90")


def test_tracabilite_aval_jusqu_aux_clients(chain):
    tree = services.downstream(chain["cream_a"])
    assert numbers(tree) == {
        chain["cream_a"].number,
        chain["bechamel"].number,
        chain["lasagna"].number,
    }
    lasagna = tree.children[0].children[0]
    assert lasagna.shipments[0]["warehouse"].code == "ENS2-E01"
    assert lasagna.shipments[0]["quantity"] == Decimal("600")


def test_un_emballage_se_trace_aussi(chain):
    impact = services.recall_impact(chain["trays"])
    assert {item.lot for item in impact.lots} == {chain["trays"], chain["lasagna"]}


# --- Rappel produit -----------------------------------------------------------


def test_simulation_de_rappel(chain):
    impact = services.recall_impact(chain["cream_a"])

    levels = {item.lot.number: item.level for item in impact.lots}
    assert levels == {
        chain["cream_a"].number: 0,
        chain["bechamel"].number: 1,
        chain["lasagna"].number: 2,
    }
    stock = {item.lot.number: item.stock_total for item in impact.lots}
    assert stock[chain["lasagna"].number] == Decimal("400")  # 1000 fabriqués − 600 livrés
    assert stock[chain["cream_a"].number] == Decimal("80")
    assert [(d["warehouse"].code, d["quantity"]) for d in impact.deliveries] == [
        ("ENS2-E01", Decimal("600"))
    ]
    # La simulation ne change rien
    assert Lot.objects.get(pk=chain["lasagna"].pk).status == LotStatus.RELEASED


def test_lancer_un_rappel_bloque_les_lots_avec_du_stock(chain, make_user):
    recall = services.launch_recall(
        chain["cream_a"], reason="Listeria signalée par le fournisseur", user=make_user("qualite")
    )
    assert recall.number.startswith("RAP-")
    blocked = set(recall.blocked_lots.values_list("number", flat=True))
    assert blocked == {chain["cream_a"].number, chain["bechamel"].number, chain["lasagna"].number}
    lasagna = Lot.objects.get(pk=chain["lasagna"].pk)
    assert lasagna.status == LotStatus.BLOCKED
    assert lasagna.block_reason.startswith(f"Rappel {recall.number}")
    # L'autre lot de crème n'est pas concerné
    assert Lot.objects.get(pk=chain["cream_b"].pk).status == LotStatus.RELEASED
    assert recall.snapshot["customers"][0]["code"] == "ENS2"


def test_un_rappel_exige_un_motif_et_ne_se_modifie_pas(chain):
    with pytest.raises(ValidationError):
        services.launch_recall(chain["cream_a"], reason=" ")
    recall = services.launch_recall(chain["cream_a"], reason="Contamination")
    recall.reason = "autre"
    with pytest.raises(ValidationError):
        recall.save()
    with pytest.raises(ValidationError):
        recall.delete()


def test_export_csv_des_clients_a_prevenir(chain):
    recall = services.launch_recall(chain["cream_a"], reason="Contamination")
    content = services.recall_csv(recall)
    lines = content.lstrip("﻿").splitlines()
    assert lines[0].startswith("Code enseigne;Enseigne;Code entrepôt")
    assert "ENS2;Marché Plus;ENS2-E01" in lines[1]
    assert ";600,000;u;" in lines[1]


def test_scenario_de_reference_creme_contaminee(db):
    """CLAUDE.md : un fournisseur signale un lot de crème contaminé.

    L'ERP liste tous les produits finis fabriqués avec ce lot, leurs stocks restants et les
    enseignes livrées, avec les quantités — en quelques secondes.
    """
    call_command("charger_donnees_demo")
    cream = Lot.objects.get(supplier_lot_number="CB-0412")

    start = time.perf_counter()
    impact = services.recall_impact(cream)
    duration = time.perf_counter() - start

    finished = {
        item.lot.article.code: item.stock_total
        for item in impact.lots
        if item.lot.article.article_type == "PF"
    }
    assert finished == {
        "PF-PAT-LASBOL-BRE-300": Decimal("54"),  # 1000 fabriqués − 850 − 96 livrés (7b)
        "PF-PAT-LASBOL-ENS1-300": Decimal("80"),  # 500 fabriqués − 300 − 120 livrés (7b)
    }
    # Le gratin dauphinois est fait avec l'autre lot de crème : il n'est pas concerné
    assert "PF-GRA-GRADAU-BRE-1000" not in finished

    delivered = {
        (d["warehouse"].code, d["lot"].article.code): d["quantity"] for d in impact.deliveries
    }
    assert delivered == {
        ("ENS1-E01", "PF-PAT-LASBOL-BRE-300"): Decimal("400"),
        ("ENS1-E02", "PF-PAT-LASBOL-ENS1-300"): Decimal("300"),
        ("ENS2-E03", "PF-PAT-LASBOL-BRE-300"): Decimal("300"),
        ("ENS3-E02", "PF-PAT-LASBOL-BRE-300"): Decimal("150"),
        # Livraisons de la démonstration de la partie 7b (préparation et expédition)
        ("ENS1-E01", "PF-PAT-LASBOL-ENS1-300"): Decimal("120"),
        ("ENS2-E01", "PF-PAT-LASBOL-BRE-300"): Decimal("96"),
    }
    assert duration < 2, f"Rappel trop lent : {duration:.2f} s"

    recall = services.launch_recall(cream, reason="Listeria signalée par le fournisseur")
    # Crème, béchamel de la phase 5, 2 lots de lasagnes, et les 2 béchamels des OF de
    # démonstration (phase 6) qui ont consommé ce lot de crème en FEFO
    blocked = {lot.article.code for lot in recall.blocked_lots.all()}
    assert blocked == {
        "MP-LAI-CREME35", "SF-BECHAMEL", "PF-PAT-LASBOL-BRE-300", "PF-PAT-LASBOL-ENS1-300",
    }  # fmt: skip
    assert recall.blocked_lots.filter(article__code="SF-BECHAMEL").count() == 3
    assert ProductRecall.objects.count() == 1


# --- Allergènes -----------------------------------------------------------------


def test_allergenes_calcules_a_travers_la_nomenclature(chain, finished_product, cream):
    lait = Allergen.objects.get(code="lait")
    cream.allergens.add(lait)

    result = services.compute_allergens(finished_product)
    assert [row["allergen"].code for row in result] == ["lait"]
    assert result[0]["sources"] == [["SF-BECHAMEL", "MP-LAI-CREME35"]]


def test_un_allergene_ajoute_sur_une_matiere_se_repercute_tout_de_suite(
    chain, finished_product, cream
):
    assert services.compute_allergens(finished_product) == []
    cream.allergens.add(Allergen.objects.get(code="oeufs"))
    assert [row["allergen"].code for row in services.compute_allergens(finished_product)] == [
        "oeufs"
    ]
