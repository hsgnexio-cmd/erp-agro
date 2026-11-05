"""Schéma « bi » : vues SQL en lecture seule des indicateurs (phase 8).

Le SQL est dans pilotage/sql/bi_views.sql. Pour modifier une vue plus tard : changer le
fichier, puis créer une nouvelle migration qui supprime le schéma et relance le fichier
(une vue PostgreSQL ne peut pas changer ses colonnes avec CREATE OR REPLACE).
"""

from pathlib import Path

from django.db import migrations

SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "bi_views.sql"


def create_views(apps, schema_editor):
    schema_editor.execute(SQL_FILE.read_text(encoding="utf-8"))


def drop_views(apps, schema_editor):
    schema_editor.execute("DROP SCHEMA IF EXISTS bi CASCADE")


class Migration(migrations.Migration):
    dependencies = [
        ("referentiel", "0004_historicalproductionline_productionline"),
        ("stocks", "0006_alter_alert_alert_type_and_more"),
        ("achats", "0001_initial"),
        ("ventes", "0002_shipment_pallet_shipmentline_palletline_and_more"),
        ("production", "0001_initial"),
        ("qualite", "0001_initial"),
    ]

    operations = [migrations.RunPython(create_views, drop_views)]
