from django.apps import AppConfig
from django.db.models.signals import post_migrate


def sync_role_permissions(**kwargs) -> None:
    from comptes.permissions import sync_group_permissions
    from comptes.roles import Role

    # Dans l'administration, seuls les tarifs de vente se saisissent (commercial, admin)
    sync_group_permissions("ventes", {"saleprice": [Role.ADMIN, Role.COMMERCIAL]})


class VentesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ventes"
    verbose_name = "Ventes"

    def ready(self) -> None:
        post_migrate.connect(sync_role_permissions, sender=self)
