from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from pilotage.bi_access import create_or_update_user


class Command(BaseCommand):
    help = (
        "Crée (ou met à jour) l'utilisateur PostgreSQL en lecture seule de Power BI / Excel, "
        "à partir de BI_DB_USER et BI_DB_PASSWORD du fichier .env. Relançable."
    )

    def handle(self, *args, **options) -> None:
        name = settings.BI_DB_USER
        try:
            created = create_or_update_user(name, settings.BI_DB_PASSWORD)
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from error
        action = "créé" if created else "mis à jour (mot de passe et droits)"
        self.stdout.write(self.style.SUCCESS(f"Utilisateur {name} {action}."))
        self.stdout.write(
            "Connexion Power BI / Excel : serveur localhost, base "
            f"{settings.DATABASES['default']['NAME']}, utilisateur {name}, mot de passe "
            "BI_DB_PASSWORD du fichier .env. Lecture du schéma bi uniquement."
        )
