"""Règles sur les sites, emplacements, enseignes et fournisseurs."""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from referentiel.choices import ArticleType, SiteType, TemperatureClass, Unit
from referentiel.models import (
    Article,
    Customer,
    CustomerWarehouse,
    Location,
    ProductFamily,
    Site,
    Supplier,
    SupplierArticle,
)


def test_le_code_site_fait_3_lettres(db):
    with pytest.raises(ValidationError):
        Site.objects.create(code="NANT", name="Nantes", site_type=SiteType.FACTORY)


def test_un_emplacement_commence_par_le_code_du_site(factory_site):
    with pytest.raises(ValidationError) as exc:
        Location.objects.create(
            site=factory_site,
            code="REN-CF-01",
            name="Chambre froide",
            temperature_class=TemperatureClass.CHILLED,
        )
    assert "NAN-" in exc.value.message_dict["code"][0]


def test_temperature_mini_inferieure_a_maxi(factory_site):
    with pytest.raises(ValidationError):
        Location.objects.create(
            site=factory_site,
            code="NAN-CF-01",
            name="Chambre froide",
            temperature_class=TemperatureClass.CHILLED,
            min_temperature=Decimal("4"),
            max_temperature=Decimal("0"),
        )


def test_une_famille_est_fabriquee_dans_une_usine(db):
    platform = Site.objects.create(code="PFN", name="Plateforme", site_type=SiteType.PLATFORM)
    with pytest.raises(ValidationError):
        ProductFamily.objects.create(code="PAT", name="Pâtes", site=platform)


def test_la_dlc_minimale_client_est_un_pourcentage(db):
    with pytest.raises(ValidationError):
        Customer.objects.create(
            code="ENS9",
            name="Test",
            customer_type="hyper",
            sells_brand=True,
            min_remaining_shelf_life_pct=Decimal("120"),
        )


def test_une_enseigne_vend_au_moins_une_marque(db):
    with pytest.raises(ValidationError):
        Customer.objects.create(
            code="ENS9",
            name="Test",
            customer_type="hyper",
            sells_brand=False,
            sells_private_label=False,
            min_remaining_shelf_life_pct=Decimal("70"),
        )


def test_un_entrepot_commence_par_le_code_de_l_enseigne(private_label_customer):
    with pytest.raises(ValidationError):
        CustomerWarehouse.objects.create(
            customer=private_label_customer, code="ENS1-E01", name="Entrepôt", city="Nantes"
        )


def test_un_fournisseur_audite_a_une_date_d_audit(db):
    with pytest.raises(ValidationError):
        Supplier.objects.create(code="FOU-001", name="Test", lead_time_days=2, audited=True)
    Supplier.objects.create(
        code="FOU-001",
        name="Test",
        lead_time_days=2,
        audited=True,
        last_audit_date=date(2026, 3, 15),
    )


def test_un_fournisseur_ne_livre_pas_de_produit_fini(finished_product):
    supplier = Supplier.objects.create(code="FOU-001", name="Test", lead_time_days=2)
    with pytest.raises(ValidationError):
        SupplierArticle.objects.create(supplier=supplier, article=finished_product)


def test_un_seul_fournisseur_principal_par_article(cream):
    first = Supplier.objects.create(code="FOU-001", name="A", lead_time_days=2)
    second = Supplier.objects.create(code="FOU-002", name="B", lead_time_days=2)
    SupplierArticle.objects.create(supplier=first, article=cream, is_main_supplier=True)
    with pytest.raises(ValidationError):
        SupplierArticle.objects.create(supplier=second, article=cream, is_main_supplier=True)
    SupplierArticle.objects.create(supplier=second, article=cream, is_main_supplier=False)


def test_les_14_allergenes_reglementaires_existent(db):
    from referentiel.models import Allergen

    assert Allergen.objects.count() == 14
    assert Allergen.objects.filter(code="lait").exists()


def test_un_emballage_est_gere_a_l_unite_sans_categorie(dairy):
    with pytest.raises(ValidationError):
        Article.objects.create(
            code="EM-BARQ-300N",
            name="Barquette",
            article_type=ArticleType.PACKAGING,
            unit=Unit.UNIT,
            category=dairy,
        )
