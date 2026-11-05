"""Fonctions de valorisation du schéma « bi » exécutées avec les droits de leur propriétaire.

L'utilisateur PostgreSQL de Power BI ne lit que le schéma bi : sans cela, les vues qui
valorisent les stocks échoueraient en lisant les tarifs (tables de l'application).
"""

from django.db import migrations

FUNCTIONS = [
    "bi.purchase_price(bigint, bigint, date)",
    "bi.sale_price(bigint, date)",
    "bi.bom_cost(bigint, date)",
    "bi.unit_value(bigint, bigint, date)",
]


class Migration(migrations.Migration):
    dependencies = [("pilotage", "0001_vues_bi")]

    operations = [
        migrations.RunSQL(
            [f"ALTER FUNCTION {f} SECURITY DEFINER SET search_path = public, bi" for f in FUNCTIONS],
            reverse_sql=[f"ALTER FUNCTION {f} SECURITY INVOKER RESET search_path" for f in FUNCTIONS],
        )
    ]
