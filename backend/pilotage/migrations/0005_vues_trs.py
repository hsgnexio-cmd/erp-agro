"""Vues du TRS (phase 10) : bi.fact_line_stop et bi.fact_line_time.

Relance tout pilotage/sql/bi_views.sql (CREATE OR REPLACE) ; les deux vues sont ajoutées en fin
de fichier.
"""

from pathlib import Path

from django.db import migrations

SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "bi_views.sql"


def recreate_views(apps, schema_editor):
    schema_editor.execute(SQL_FILE.read_text(encoding="utf-8"))


def drop_oee_views(apps, schema_editor):
    schema_editor.execute(
        "DROP VIEW IF EXISTS bi.fact_line_time; DROP VIEW IF EXISTS bi.fact_line_stop;"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("pilotage", "0004_vues_previsions"),
        ("production", "0003_arrets_de_ligne_et_trs"),
    ]

    operations = [migrations.RunPython(recreate_views, drop_oee_views)]
