from django.core.management.base import BaseCommand

from achats.demo_data import load_demo_data as load_purchasing
from comptes.demo_users import load_demo_data as load_team
from pilotage.demo_history import load_demo_data as load_history
from previsions.demo_data import load_demo_data as load_forecasts
from production.demo_data import load_demo_data as load_production
from production.demo_plan import load_demo_data as load_master_plan
from qualite.demo_tracabilite import load_demo_data as load_traceability
from referentiel.demo_data import load_demo_data as load_referential
from stocks.demo_data import load_demo_data as load_stocks
from stocks.demo_monitoring import load_demo_data as load_monitoring
from ventes.demo_data import load_demo_data as load_sales
from ventes.demo_shipping import load_demo_data as load_shipping


class Command(BaseCommand):
    help = "Charge toutes les données fictives de démonstration, sans doublons."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--sans-historique",
            action="store_true",
            dest="sans_historique",
            help="Ne rejoue pas les 6 semaines d'historique (plus rapide, utilisé par les tests).",
        )

    def handle(self, *args, **options) -> None:
        loaders = [
            ("Équipe (comptes de démonstration)", load_team),
            ("Référentiel", load_referential),
            ("Achats", load_purchasing),
            ("Stocks", load_stocks),
            ("Surveillance", load_monitoring),
            ("Traçabilité", load_traceability),
            ("Production", load_production),
            ("Ventes", load_sales),
            ("Expéditions", load_shipping),
            ("Prévisions", load_forecasts),
        ]
        if not options["sans_historique"]:
            # En dernier : l'historique s'appuie sur tout le reste (tarifs, référentiel…)
            loaders.append(("Historique (6 semaines)", load_history))
        # Après l'historique : le plan s'appuie sur ses prévisions figées et son stock
        loaders.append(("Plan de production (semaine prochaine)", load_master_plan))
        for title, loader in loaders:
            counts = loader()
            self.stdout.write(self.style.SUCCESS(f"{title} :"))
            for label, count in counts.items():
                self.stdout.write(f"  - {label} : {count}")
