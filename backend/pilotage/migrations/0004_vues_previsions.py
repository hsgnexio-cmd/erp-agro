"""Vues des prévisions de vente (phase 9a) : bi.fact_forecast et bi.fact_forecast_accuracy.

Relance tout pilotage/sql/bi_views.sql : chaque objet y est créé avec CREATE OR REPLACE, et
les deux nouvelles vues sont ajoutées en fin de fichier.
"""

from pathlib import Path

from django.db import migrations

SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "bi_views.sql"


def recreate_views(apps, schema_editor):
    schema_editor.execute(SQL_FILE.read_text(encoding="utf-8"))


def drop_forecast_views(apps, schema_editor):
    schema_editor.execute(
        "DROP VIEW IF EXISTS bi.fact_forecast_accuracy; DROP VIEW IF EXISTS bi.fact_forecast;"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("pilotage", "0003_valeur_du_stock_journalier"),
        ("previsions", "0001_initial"),
    ]

    operations = [migrations.RunPython(recreate_views, drop_forecast_views)]
