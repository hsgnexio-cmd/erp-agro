from django.core.management.base import BaseCommand

from ventes.edi import simulate_day


class Command(BaseCommand):
    help = "Simule tout de suite la réception des commandes EDI des enseignes."

    def handle(self, *args, **options) -> None:
        for message in simulate_day():
            line = f"  - {message.message_id} : {message.get_status_display()}"
            if message.errors:
                line += f" ({' ; '.join(message.errors)})"
            self.stdout.write(line)
