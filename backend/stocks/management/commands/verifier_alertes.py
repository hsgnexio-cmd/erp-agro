from django.core.management.base import BaseCommand

from stocks.monitoring import run_daily_checks


class Command(BaseCommand):
    help = "Lance tout de suite les vérifications quotidiennes (péremption, relevés manquants)."

    def handle(self, *args, **options) -> None:
        counts = run_daily_checks()
        self.stdout.write(self.style.SUCCESS("Vérifications terminées. Nouvelles alertes :"))
        for label, count in counts.items():
            self.stdout.write(f"  - {label} : {count}")
