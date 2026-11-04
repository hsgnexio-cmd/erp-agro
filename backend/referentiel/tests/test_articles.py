"""Règles sur les articles : codification (section 5), DLC/DDM (règle 3), MDD (règle 10)."""

import pytest
from django.core.exceptions import ValidationError

from referentiel.choices import ArticleType, DateType, TemperatureClass, Unit
from referentiel.models import Article


def errors_of(exc: pytest.ExceptionInfo) -> dict:
    return exc.value.message_dict


# --- Codification ------------------------------------------------------------


def test_le_code_produit_fini_est_genere_automatiquement(finished_product):
    assert finished_product.code == "PF-PAT-LASBOL-BRE-300"


def test_le_code_produit_fini_mdd_contient_l_enseigne(recipe, private_label_customer):
    article = Article.objects.create(
        name="Lasagnes 1 kg MDD",
        article_type=ArticleType.FINISHED_PRODUCT,
        unit=Unit.UNIT,
        recipe=recipe,
        brand_customer=private_label_customer,
        format_size=1000,
        shelf_life_days=14,
    )
    assert article.code == "PF-PAT-LASBOL-ENS2-1000"
    assert article.brand_code == "ENS2"


def test_un_code_produit_fini_saisi_a_la_main_est_remplace(recipe):
    article = Article.objects.create(
        code="N-IMPORTE-QUOI",
        name="Lasagnes",
        article_type=ArticleType.FINISHED_PRODUCT,
        unit=Unit.UNIT,
        recipe=recipe,
        format_size=300,
        shelf_life_days=14,
    )
    assert article.code == "PF-PAT-LASBOL-BRE-300"


def test_le_code_matiere_doit_reprendre_sa_categorie(dairy):
    with pytest.raises(ValidationError) as exc:
        Article.objects.create(
            code="MP-VIA-CREME",
            name="Crème",
            article_type=ArticleType.RAW_MATERIAL,
            unit=Unit.KG,
            category=dairy,
            shelf_life_days=21,
        )
    assert "MP-LAI-[CODE]" in errors_of(exc)["code"][0]


def test_le_code_est_mis_en_majuscules(dairy):
    article = Article.objects.create(
        code="mp-lai-lait",
        name="Lait",
        article_type=ArticleType.RAW_MATERIAL,
        unit=Unit.LITRE,
        category=dairy,
        shelf_life_days=10,
    )
    assert article.code == "MP-LAI-LAIT"


@pytest.mark.parametrize(
    ("article_type", "code", "valid"),
    [
        (ArticleType.SEMI_FINISHED, "SF-SAUCEBOL", True),
        (ArticleType.SEMI_FINISHED, "SAUCEBOL", False),
        (ArticleType.PACKAGING, "EM-BARQ-300N", True),
        (ArticleType.PACKAGING, "EM-BARQ", False),
    ],
)
def test_format_des_codes_semi_finis_et_emballages(db, article_type, code, valid):
    article = Article(
        code=code,
        name="Test",
        article_type=article_type,
        unit=Unit.KG if article_type == ArticleType.SEMI_FINISHED else Unit.UNIT,
        shelf_life_days=3 if article_type == ArticleType.SEMI_FINISHED else None,
    )
    if valid:
        article.save()
    else:
        with pytest.raises(ValidationError) as exc:
            article.save()
        assert "code" in errors_of(exc)


def test_deux_articles_ne_peuvent_pas_avoir_le_meme_code(cream, dairy):
    with pytest.raises(ValidationError):
        Article.objects.create(
            code="MP-LAI-CREME35",
            name="Doublon",
            article_type=ArticleType.RAW_MATERIAL,
            unit=Unit.KG,
            category=dairy,
            shelf_life_days=21,
        )


# --- DLC / DDM ----------------------------------------------------------------


def test_un_produit_sec_est_gere_en_ddm(flour):
    assert flour.date_type == DateType.DDM
    assert flour.storage_temperature_class == TemperatureClass.AMBIENT


def test_un_produit_frais_est_gere_en_dlc(cream):
    assert cream.date_type == DateType.DLC
    assert cream.storage_temperature_class == TemperatureClass.CHILLED


def test_un_produit_fini_est_gere_en_dlc(finished_product):
    assert finished_product.date_type == DateType.DLC


def test_la_duree_de_vie_est_obligatoire(dairy):
    with pytest.raises(ValidationError) as exc:
        Article.objects.create(
            code="MP-LAI-LAIT",
            name="Lait",
            article_type=ArticleType.RAW_MATERIAL,
            unit=Unit.LITRE,
            category=dairy,
        )
    assert "shelf_life_days" in errors_of(exc)


def test_un_emballage_n_a_pas_de_duree_de_vie(db):
    with pytest.raises(ValidationError) as exc:
        Article.objects.create(
            code="EM-BARQ-300N",
            name="Barquette",
            article_type=ArticleType.PACKAGING,
            unit=Unit.UNIT,
            shelf_life_days=30,
        )
    assert "shelf_life_days" in errors_of(exc)


# --- Champs propres à chaque type ---------------------------------------------


def test_une_matiere_premiere_doit_avoir_une_categorie(db):
    with pytest.raises(ValidationError) as exc:
        Article.objects.create(
            code="MP-LAI-LAIT",
            name="Lait",
            article_type=ArticleType.RAW_MATERIAL,
            unit=Unit.LITRE,
            shelf_life_days=10,
        )
    assert "category" in errors_of(exc)


def test_un_produit_fini_doit_avoir_recette_et_format(db):
    with pytest.raises(ValidationError) as exc:
        Article.objects.create(
            name="Lasagnes",
            article_type=ArticleType.FINISHED_PRODUCT,
            unit=Unit.UNIT,
            shelf_life_days=14,
        )
    assert {"recipe", "format_size"} <= set(errors_of(exc))


def test_un_produit_fini_se_gere_a_l_unite(recipe):
    with pytest.raises(ValidationError) as exc:
        Article.objects.create(
            name="Lasagnes",
            article_type=ArticleType.FINISHED_PRODUCT,
            unit=Unit.KG,
            recipe=recipe,
            format_size=300,
            shelf_life_days=14,
        )
    assert "unit" in errors_of(exc)


def test_une_matiere_ne_peut_pas_avoir_de_recette(dairy, recipe):
    with pytest.raises(ValidationError) as exc:
        Article.objects.create(
            code="MP-LAI-LAIT",
            name="Lait",
            article_type=ArticleType.RAW_MATERIAL,
            unit=Unit.LITRE,
            category=dairy,
            recipe=recipe,
            shelf_life_days=10,
        )
    assert "recipe" in errors_of(exc)


# --- Versions MDD (règle 10) --------------------------------------------------


def test_une_recette_peut_avoir_plusieurs_versions(
    finished_product, recipe, private_label_customer
):
    Article.objects.create(
        name="Lasagnes MDD",
        article_type=ArticleType.FINISHED_PRODUCT,
        unit=Unit.UNIT,
        recipe=recipe,
        brand_customer=private_label_customer,
        format_size=300,
        shelf_life_days=14,
    )
    assert set(recipe.articles.values_list("code", flat=True)) == {
        "PF-PAT-LASBOL-BRE-300",
        "PF-PAT-LASBOL-ENS2-300",
    }


def test_pas_de_mdd_pour_une_enseigne_qui_n_en_vend_pas(recipe, brand_only_customer):
    with pytest.raises(ValidationError) as exc:
        Article.objects.create(
            name="Lasagnes Proxi",
            article_type=ArticleType.FINISHED_PRODUCT,
            unit=Unit.UNIT,
            recipe=recipe,
            brand_customer=brand_only_customer,
            format_size=300,
            shelf_life_days=14,
        )
    assert "ENS4" in errors_of(exc)["brand_customer"][0]


def test_une_enseigne_avec_des_produits_mdd_ne_peut_pas_arreter_le_mdd(
    recipe, private_label_customer
):
    Article.objects.create(
        name="Lasagnes MDD",
        article_type=ArticleType.FINISHED_PRODUCT,
        unit=Unit.UNIT,
        recipe=recipe,
        brand_customer=private_label_customer,
        format_size=300,
        shelf_life_days=14,
    )
    private_label_customer.sells_private_label = False
    with pytest.raises(ValidationError):
        private_label_customer.save()
