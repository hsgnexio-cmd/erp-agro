"""Valeur du stock dans bi.fact_stock_daily (pour les mesures Power BI des couvertures).

Relance tout pilotage/sql/bi_views.sql : chaque objet y est créé avec CREATE OR REPLACE, et
la nouvelle colonne « value » est ajoutée en fin de vue (ce que PostgreSQL accepte).
"""

from pathlib import Path

from django.db import migrations

SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "bi_views.sql"


def recreate_views(apps, schema_editor):
    schema_editor.execute(SQL_FILE.read_text(encoding="utf-8"))


class Migration(migrations.Migration):
    dependencies = [("pilotage", "0002_fonctions_bi_security_definer")]

    operations = [migrations.RunPython(recreate_views, migrations.RunPython.noop)]
