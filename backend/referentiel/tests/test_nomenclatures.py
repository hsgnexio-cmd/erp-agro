"""Règles sur les nomenclatures."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from referentiel.choices import ArticleType, Unit
from referentiel.models import Article, BillOfMaterials, BOMLine


def add_line(bom, component, quantity="1", unit=None, loss_rate="0"):
    return BOMLine.objects.create(
        bom=bom,
        component=component,
        quantity=Decimal(quantity),
        unit=unit or component.unit,
        loss_rate=Decimal(loss_rate),
    )


def test_nomenclature_multiniveau(finished_product, semi_finished, cream):
    bechamel = BillOfMaterials.objects.create(article=semi_finished, base_quantity=Decimal("100"))
    add_line(bechamel, cream, "10")
    lasagnes = BillOfMaterials.objects.create(article=finished_product)
    add_line(lasagnes, semi_finished, "0.090")

    assert lasagnes.lines.get().component.code == "SF-BECHAMEL"
    assert bechamel.lines.get().component.code == "MP-LAI-CREME35"


def test_une_matiere_n_a_pas_de_nomenclature(cream):
    with pytest.raises(ValidationError) as exc:
        BillOfMaterials.objects.create(article=cream)
    assert "article" in exc.value.message_dict


def test_un_produit_fini_ne_peut_pas_etre_composant(finished_product, semi_finished):
    bom = BillOfMaterials.objects.create(article=semi_finished)
    with pytest.raises(ValidationError) as exc:
        add_line(bom, finished_product)
    assert "component" in exc.value.message_dict


def test_un_article_ne_peut_pas_etre_son_propre_composant(semi_finished):
    bom = BillOfMaterials.objects.create(article=semi_finished)
    with pytest.raises(ValidationError):
        add_line(bom, semi_finished)


def test_les_boucles_sont_interdites(db):
    sf_a = Article.objects.create(
        code="SF-A",
        name="A",
        article_type=ArticleType.SEMI_FINISHED,
        unit=Unit.KG,
        shelf_life_days=3,
    )
    sf_b = Article.objects.create(
        code="SF-B",
        name="B",
        article_type=ArticleType.SEMI_FINISHED,
        unit=Unit.KG,
        shelf_life_days=3,
    )
    add_line(BillOfMaterials.objects.create(article=sf_a), sf_b)

    # B contiendrait A, qui contient déjà B : boucle
    with pytest.raises(ValidationError) as exc:
        add_line(BillOfMaterials.objects.create(article=sf_b), sf_a)
    assert "Boucle" in exc.value.message_dict["component"][0]


def test_l_unite_doit_etre_celle_du_composant(semi_finished, cream):
    bom = BillOfMaterials.objects.create(article=semi_finished)
    with pytest.raises(ValidationError) as exc:
        add_line(bom, cream, unit=Unit.LITRE)
    assert "unit" in exc.value.message_dict


def test_un_composant_ne_figure_qu_une_fois(semi_finished, cream):
    bom = BillOfMaterials.objects.create(article=semi_finished)
    add_line(bom, cream)
    with pytest.raises(ValidationError):
        add_line(bom, cream)


@pytest.mark.parametrize("loss_rate", ["-1", "100"])
def test_le_taux_de_perte_est_entre_0_et_100(semi_finished, cream, loss_rate):
    bom = BillOfMaterials.objects.create(article=semi_finished)
    with pytest.raises(ValidationError):
        add_line(bom, cream, loss_rate=loss_rate)


def test_la_quantite_doit_etre_positive(semi_finished, cream):
    bom = BillOfMaterials.objects.create(article=semi_finished)
    with pytest.raises(ValidationError):
        add_line(bom, cream, quantity="0")


def test_quantite_brute_avec_perte(semi_finished, cream):
    """40 kg nets avec 25 % de perte à la cuisson : il faut sortir 53,3333 kg."""
    bom = BillOfMaterials.objects.create(article=semi_finished)
    line = add_line(bom, cream, quantity="40", loss_rate="25")
    assert line.gross_quantity == Decimal("53.3333")
    assert isinstance(line.gross_quantity, Decimal)
