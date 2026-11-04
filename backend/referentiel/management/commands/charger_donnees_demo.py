from django.core.management.base import BaseCommand

from referentiel.demo_data import load_demo_data


class Command(BaseCommand):
    help = "Charge les données fictives de démonstration du référentiel (sans doublons)."

    def handle(self, *args, **options) -> None:
        counts = load_demo_data()
        self.stdout.write(self.style.SUCCESS("Données de démonstration chargées :"))
        for label, count in counts.items():
            self.stdout.write(f"  - {label} : {count}")
