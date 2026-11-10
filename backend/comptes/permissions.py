"""Outils de droits par rôle, communs à tous les modules de l'ERP."""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.permissions import SAFE_METHODS, BasePermission

from .roles import Role


def user_roles(user) -> set[str]:
    return set(user.groups.values_list("name", flat=True))


def has_any_role(user, roles) -> bool:
    """Vrai si l'utilisateur a au moins un des rôles (un superutilisateur a tous les droits)."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return bool(user_roles(user) & {str(role) for role in roles})


class WriteRolesPermission(BasePermission):
    """Lecture selon la matrice d'accès (`view.read_area`, voir comptes/access.py ; tous les
    utilisateurs connectés si la vue n'en a pas) ; écriture pour `view.write_roles`."""

    message = "Ton rôle ne permet pas cette opération."

    def get_write_roles(self, view) -> list:
        return getattr(view, "write_roles", [])

    def has_permission(self, request, view) -> bool:
        if not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            area = getattr(view, "read_area", None)
            if area is None:
                return True
            from .access import can_read

            if can_read(request.user, area):
                return True
            self.message = "Ton rôle ne donne pas accès à ces données."
            return False
        return has_any_role(request.user, self.get_write_roles(view))


def sync_group_permissions(app_label: str, write_roles: dict[str, list]) -> None:
    """Donne aux groupes (rôles) les droits Django correspondants, pour l'administration.

    - tous les rôles peuvent consulter chaque table de l'app ;
    - les rôles de `write_roles[nom_du_modèle]` peuvent ajouter et modifier ;
    - le rôle `admin` peut aussi supprimer les tables modifiables.
    """
    groups = {group.name: group for group in Group.objects.filter(name__in=Role.values)}
    if not groups:
        return
    for content_type in ContentType.objects.filter(app_label=app_label):
        if content_type.model.startswith("historical"):
            continue
        roles = [str(role) for role in write_roles.get(content_type.model, [])]
        perms = {
            p.codename.split("_")[0]: p
            for p in Permission.objects.filter(content_type=content_type)
        }
        for name, group in groups.items():
            wanted = {"view"}
            if name in roles:
                wanted |= {"add", "change"}
            if name == Role.ADMIN and roles:
                wanted.add("delete")
            for action, perm in perms.items():
                if action in wanted:
                    group.permissions.add(perm)
                else:
                    group.permissions.remove(perm)
