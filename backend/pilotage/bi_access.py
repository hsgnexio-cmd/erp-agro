"""Utilisateur PostgreSQL en lecture seule pour Power BI et Excel (phase 8b).

Il ne voit que le schéma « bi » (vues des indicateurs) : aucune table de l'application,
aucune écriture. Son mot de passe vient du fichier .env (BI_DB_PASSWORD), jamais du code.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection
from psycopg import sql

MIN_PASSWORD_LENGTH = 12
# Début des valeurs d'exemple de .env.example, à remplacer avant usage
EXAMPLE_PREFIX = "change-moi"

GRANTS = [
    "GRANT CONNECT ON DATABASE {db} TO {role}",
    "GRANT USAGE ON SCHEMA bi TO {role}",
    "GRANT SELECT ON ALL TABLES IN SCHEMA bi TO {role}",
    "GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA bi TO {role}",
    # Vues recréées plus tard par une migration : le droit de lecture suit automatiquement
    "ALTER DEFAULT PRIVILEGES IN SCHEMA bi GRANT SELECT ON TABLES TO {role}",
    # Sécurité supplémentaire : toute session de cet utilisateur est en lecture seule
    "ALTER ROLE {role} SET default_transaction_read_only = on",
]


def role_exists(name: str) -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [name])
        return cursor.fetchone() is not None


def grant_read_access(name: str) -> None:
    """Donne (ou redonne) à l'utilisateur la lecture du schéma bi, et rien d'autre."""
    database = connection.settings_dict["NAME"]
    with connection.cursor() as cursor:
        for statement in GRANTS:
            cursor.execute(
                sql.SQL(statement).format(role=sql.Identifier(name), db=sql.Identifier(database))
            )


def create_or_update_user(name: str, password: str) -> bool:
    """Crée l'utilisateur ou change son mot de passe ; renvoie True s'il vient d'être créé."""
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise ValidationError(
            f"Mot de passe de l'utilisateur {name} trop court ou absent : mets au moins "
            f"{MIN_PASSWORD_LENGTH} caractères dans BI_DB_PASSWORD (fichier .env)."
        )
    if password.startswith(EXAMPLE_PREFIX):
        raise ValidationError(
            "BI_DB_PASSWORD contient encore la valeur d'exemple de .env.example : remplace-la "
            "par un vrai mot de passe dans le fichier .env (voir README)."
        )
    created = not role_exists(name)
    verb = (
        "CREATE ROLE {role} LOGIN PASSWORD {password}"
        if created
        else ("ALTER ROLE {role} LOGIN PASSWORD {password}")
    )
    with connection.cursor() as cursor:
        cursor.execute(
            sql.SQL(verb).format(role=sql.Identifier(name), password=sql.Literal(password))
        )
    grant_read_access(name)
    return created


def refresh_grants(**kwargs) -> None:
    """Après chaque migrate : les vues recréées retrouvent leur droit de lecture.

    Sauf dans les bases de test (« test_… ») : Power BI ne s'y connecte pas, et les bases
    créées en parallèle (pytest-xdist) modifieraient en même temps ce rôle commun au serveur.
    """
    if connection.settings_dict["NAME"].startswith("test_"):
        return
    if connection.vendor == "postgresql" and role_exists(settings.BI_DB_USER):
        grant_read_access(settings.BI_DB_USER)
