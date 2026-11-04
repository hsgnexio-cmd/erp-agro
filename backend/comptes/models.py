from django.contrib.auth.models import AbstractUser

from .roles import Role


class User(AbstractUser):
    """Utilisateur de l'ERP.

    Ses rôles sont les groupes Django auxquels il appartient (voir comptes/roles.py).
    """

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"

    def has_role(self, role: Role | str) -> bool:
        """Indique si l'utilisateur possède ce rôle."""
        return self.groups.filter(name=str(role)).exists()
