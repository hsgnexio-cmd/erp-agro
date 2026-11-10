"""Équipe de démonstration de Brévanne Traiteur : un compte par personne, avec son rôle.

Les 7 rôles de l'ERP (comptes/roles.py) commandent les droits de chaque écran ; comme dans une
vraie entreprise, plusieurs personnes peuvent avoir le même rôle (un responsable de production
par usine…). Tous ces comptes partagent le mot de passe de démonstration DEMO_USERS_PASSWORD
du fichier .env : ce sont des comptes de test, jamais des comptes réels. Le compte
administrateur est créé à part (createsuperuser), avec son propre mot de passe.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction

from .roles import Role

MIN_PASSWORD_LENGTH = 8

# (identifiant, prénom, nom, fonction, rôles)
TEAM = [
    ("helene.morvan", "Hélène", "Morvan", "Directrice générale", [Role.DIRECTION]),
    ("pierre.kerjean", "Pierre", "Kerjean", "Directeur administratif et financier",
     [Role.DIRECTION]),
    ("julien.legoff", "Julien", "Le Goff", "Acheteur matières et emballages", [Role.ACHETEUR]),
    ("sandrine.prigent", "Sandrine", "Prigent", "Cheffe de quai, plateforme PFN",
     [Role.MAGASINIER]),
    ("yann.tanguy", "Yann", "Tanguy", "Magasinier, entrepôt matières MPE", [Role.MAGASINIER]),
    ("marc.guillou", "Marc", "Guillou", "Responsable de production, usine NAN",
     [Role.PRODUCTION]),
    ("anne.perrot", "Anne", "Perrot", "Responsable de production, usine REN",
     [Role.PRODUCTION]),
    ("claire.lebihan", "Claire", "Le Bihan", "Responsable qualité", [Role.QUALITE]),
    ("thomas.riou", "Thomas", "Riou", "Commercial grands comptes", [Role.COMMERCIAL]),
    ("lea.nedelec", "Léa", "Nédélec", "Administration des ventes et prévisions",
     [Role.COMMERCIAL]),
]  # fmt: skip


@transaction.atomic
def load_demo_data(password: str | None = None) -> dict[str, int | str]:
    """Crée les comptes de l'équipe ; relançable : un compte existant n'est pas modifié."""
    password = password if password is not None else settings.DEMO_USERS_PASSWORD
    if len(password or "") < MIN_PASSWORD_LENGTH:
        return {
            "comptes de démonstration": (
                "aucun : indique DEMO_USERS_PASSWORD (8 caractères au moins) dans le fichier .env"
            )
        }
    user_model = get_user_model()
    created = 0
    for username, first_name, last_name, job_title, roles in TEAM:
        if user_model.objects.filter(username=username).exists():
            continue
        user = user_model.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            job_title=job_title,
        )
        user.groups.add(*Group.objects.filter(name__in=[str(role) for role in roles]))
        created += 1
    return {"comptes de démonstration créés": created, "équipe au total": len(TEAM)}
