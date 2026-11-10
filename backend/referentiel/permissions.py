"""Qui peut modifier quoi dans le référentiel.

Tous les utilisateurs connectés peuvent consulter. Seuls les rôles listés ici
peuvent créer ou modifier. Le rôle `direction` consulte sans modifier.
Personne ne supprime via l'API : on désactive (champ « actif »).
"""

from comptes.permissions import WriteRolesPermission, has_any_role, sync_group_permissions
from comptes.roles import Role

ADMIN = [Role.ADMIN]
TECHNICAL = [Role.ADMIN, Role.PRODUCTION, Role.QUALITE]
PURCHASING = [Role.ADMIN, Role.ACHETEUR]
SALES = [Role.ADMIN, Role.COMMERCIAL]

# Nom technique du modèle → rôles autorisés à créer / modifier
WRITE_ROLES: dict[str, list[Role]] = {
    "site": ADMIN,
    "siteclosure": ADMIN,
    "location": ADMIN,
    "productfamily": ADMIN,
    "materialcategory": ADMIN,
    "allergen": [],  # liste réglementaire fixe
    "recipe": TECHNICAL,
    "article": TECHNICAL,
    "billofmaterials": TECHNICAL,
    "bomline": TECHNICAL,
    "supplier": PURCHASING,
    "supplierarticle": PURCHASING,
    "customer": SALES,
    "customerwarehouse": SALES,
    "documentsequence": [],  # numérotation automatique, jamais modifiée à la main
    "productionline": [Role.ADMIN, Role.PRODUCTION],
}

# Règle 8 : les allergènes d'une matière sont validés par la qualité
ALLERGEN_ROLES = [Role.ADMIN, Role.QUALITE]


def can_write(user, model) -> bool:
    return has_any_role(user, WRITE_ROLES.get(model._meta.model_name, []))


def can_edit_allergens(user) -> bool:
    return has_any_role(user, ALLERGEN_ROLES)


class ReferentielPermission(WriteRolesPermission):
    """Lecture pour tous les utilisateurs connectés, écriture selon WRITE_ROLES."""

    message = "Ton rôle ne permet pas de modifier ces données."

    def get_write_roles(self, view) -> list:
        return WRITE_ROLES.get(view.queryset.model._meta.model_name, [])


def sync_role_permissions(**kwargs) -> None:
    """Applique WRITE_ROLES aux groupes Django (lancé après chaque `migrate`)."""
    sync_group_permissions("referentiel", WRITE_ROLES)
