"""Taux de service en jours ouvrés (phase 11) : bi.fact_service lit la date limite d'expédition
de la commande (samedi pour une livraison le lundi) au lieu de « la veille ».

Relance tout pilotage/sql/bi_views.sql (CREATE OR REPLACE, mêmes colonnes).
"""

from pathlib import Path

from django.db import migrations

SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "bi_views.sql"


def recreate_views(apps, schema_editor):
    schema_editor.execute(SQL_FILE.read_text(encoding="utf-8"))


class Migration(migrations.Migration):
    dependencies = [
        ("pilotage", "0005_vues_trs"),
        ("ventes", "0003_date_limite_expedition"),
    ]

    operations = [migrations.RunPython(recreate_views, migrations.RunPython.noop)]
