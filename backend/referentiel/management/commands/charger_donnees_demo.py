from django.core.management.base import BaseCommand

from achats.demo_data import load_demo_data as load_purchasing
from referentiel.demo_data import load_demo_data as load_referential


class Command(BaseCommand):
    help = "Charge les données fictives de démonstration (référentiel, achats), sans doublons."

    def handle(self, *args, **options) -> None:
        for title, loader in (("Référentiel", load_referential), ("Achats", load_purchasing)):
            counts = loader()
            self.stdout.write(self.style.SUCCESS(f"{title} :"))
            for label, count in counts.items():
                self.stdout.write(f"  - {label} : {count}")
