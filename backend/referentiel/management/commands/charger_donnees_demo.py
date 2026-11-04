from django.core.management.base import BaseCommand

from achats.demo_data import load_demo_data as load_purchasing
from production.demo_data import load_demo_data as load_production
from qualite.demo_tracabilite import load_demo_data as load_traceability
from referentiel.demo_data import load_demo_data as load_referential
from stocks.demo_data import load_demo_data as load_stocks
from stocks.demo_monitoring import load_demo_data as load_monitoring


class Command(BaseCommand):
    help = "Charge toutes les données fictives de démonstration, sans doublons."

    def handle(self, *args, **options) -> None:
        for title, loader in (
            ("Référentiel", load_referential),
            ("Achats", load_purchasing),
            ("Stocks", load_stocks),
            ("Surveillance", load_monitoring),
            ("Traçabilité", load_traceability),
            ("Production", load_production),
        ):
            counts = loader()
            self.stdout.write(self.style.SUCCESS(f"{title} :"))
            for label, count in counts.items():
                self.stdout.write(f"  - {label} : {count}")
