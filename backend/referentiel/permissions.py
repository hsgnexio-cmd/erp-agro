"""Qui peut modifier quoi dans le référentiel.

Tous les utilisateurs connectés peuvent consulter. Seuls les rôles listés ici
peuvent créer ou modifier. Le rôle `direction` consulte sans modifier.
Personne ne supprime via l'API : on désactive (champ « actif »).
"""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.permissions import SAFE_METHODS, BasePermission

from comptes.roles import Role

ADMIN = [Role.ADMIN]
TECHNICAL = [Role.ADMIN, Role.PRODUCTION, Role.QUALITE]
PURCHASING = [Role.ADMIN, Role.ACHETEUR]
SALES = [Role.ADMIN, Role.COMMERCIAL]

# Nom technique du modèle → rôles autorisés à créer / modifier
WRITE_ROLES: dict[str, list[Role]] = {
    "site": ADMIN,
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
}

# Règle 8 : les allergènes d'une matière sont validés par la qualité
ALLERGEN_ROLES = [Role.ADMIN, Role.QUALITE]


def user_roles(user) -> set[str]:
    return set(user.groups.values_list("name", flat=True))


def has_any_role(user, roles) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return bool(user_roles(user) & {str(role) for role in roles})


def can_write(user, model) -> bool:
    return has_any_role(user, WRITE_ROLES.get(model._meta.model_name, []))


def can_edit_allergens(user) -> bool:
    return has_any_role(user, ALLERGEN_ROLES)


class ReferentielPermission(BasePermission):
    """Lecture pour tous les utilisateurs connectés, écriture selon WRITE_ROLES."""

    message = "Ton rôle ne permet pas de modifier ces données."

    def has_permission(self, request, view) -> bool:
        if not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return can_write(request.user, view.queryset.model)


def sync_role_permissions(**kwargs) -> None:
    """Donne aux groupes (rôles) les droits Django correspondants, pour l'administration.

    Lancé automatiquement après chaque `migrate`.
    """
    groups = {group.name: group for group in Group.objects.filter(name__in=Role.values)}
    if not groups:
        return
    for model_name, write_roles in WRITE_ROLES.items():
        try:
            content_type = ContentType.objects.get(app_label="referentiel", model=model_name)
        except ContentType.DoesNotExist:
            continue
        perms = {
            p.codename.split("_")[0]: p
            for p in Permission.objects.filter(content_type=content_type)
        }
        for name, group in groups.items():
            wanted = {"view"}
            if name in write_roles:
                wanted |= {"add", "change"}
            if name == Role.ADMIN and write_roles:
                wanted.add("delete")
            for action, perm in perms.items():
                if action in wanted:
                    group.permissions.add(perm)
                else:
                    group.permissions.remove(perm)
