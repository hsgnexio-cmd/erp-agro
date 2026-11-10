from django.core.management.base import BaseCommand

from comptes.demo_users import load_demo_data


class Command(BaseCommand):
    help = "Crée l'équipe de démonstration (un compte par personne, avec son rôle), sans doublon."

    def handle(self, *args, **options) -> None:
        for label, count in load_demo_data().items():
            self.stdout.write(f"{label} : {count}")
