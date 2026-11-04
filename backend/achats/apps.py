from django.apps import AppConfig
from django.db.models.signals import post_migrate


def sync_role_permissions(**kwargs) -> None:
    from comptes.permissions import sync_group_permissions
    from comptes.roles import Role

    # Dans l'administration, seuls les tarifs se saisissent (acheteur, admin)
    sync_group_permissions("achats", {"supplierprice": [Role.ADMIN, Role.ACHETEUR]})


class AchatsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "achats"
    verbose_name = "Achats et réceptions"

    def ready(self) -> None:
        post_migrate.connect(sync_role_permissions, sender=self)
