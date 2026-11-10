"""Utilisateur PostgreSQL de Power BI : lecture du schéma bi seulement (phase 8b)."""

import secrets

import psycopg
import pytest
from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.db import connection
from django.test import override_settings
from psycopg import sql

from pilotage.bi_access import create_or_update_user, role_exists

ROLE = "powerbi_test"


def _connect(password: str):
    settings = connection.settings_dict
    return psycopg.connect(
        host=settings["HOST"],
        port=settings["PORT"],
        dbname=settings["NAME"],
        user=ROLE,
        password=password,
        autocommit=True,
    )


@pytest.fixture
def bi_role(transactional_db):
    """Utilisateur de test, supprimé à la fin (un rôle PostgreSQL vaut pour tout le serveur)."""
    password = secrets.token_urlsafe(16)
    create_or_update_user(ROLE, password)
    yield password
    with connection.cursor() as cursor:
        cursor.execute(sql.SQL("DROP OWNED BY {}").format(sql.Identifier(ROLE)))
        cursor.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(ROLE)))


def test_l_utilisateur_bi_lit_les_vues_et_les_valorisations(bi_role):
    with _connect(bi_role) as conn:
        assert conn.execute("SELECT count(*) FROM bi.fact_service").fetchone() == (0,)
        assert conn.execute("SELECT count(*) FROM bi.dim_article").fetchone() == (0,)
        # Les fonctions de valorisation lisent les tarifs avec les droits de l'ERP
        assert conn.execute("SELECT bi.unit_value(1, NULL, current_date)").fetchone() == (None,)


def test_l_utilisateur_bi_ne_voit_pas_les_tables_et_n_ecrit_rien(bi_role):
    with _connect(bi_role) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT * FROM stocks_lot")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT * FROM comptes_user")
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            conn.execute("CREATE TABLE bi.essai (id int)")


def test_relancer_change_le_mot_de_passe_sans_doublon(bi_role):
    new_password = secrets.token_urlsafe(16)
    assert create_or_update_user(ROLE, new_password) is False
    with _connect(new_password) as conn:
        assert conn.execute("SELECT 1").fetchone() == (1,)
    with pytest.raises(psycopg.OperationalError):
        _connect(bi_role)


def test_mot_de_passe_obligatoire(db):
    with pytest.raises(ValidationError, match="au moins 12 caractères"):
        create_or_update_user(ROLE, "court")
    with pytest.raises(ValidationError, match="valeur d'exemple"):
        create_or_update_user(ROLE, "change-moi-aussi")
    with (
        override_settings(BI_DB_USER=ROLE, BI_DB_PASSWORD=""),
        pytest.raises(CommandError, match="BI_DB_PASSWORD"),
    ):
        call_command("creer_utilisateur_bi")
    assert not role_exists(ROLE)
