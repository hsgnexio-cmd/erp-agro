from django.apps import AppConfig
from django.db.models.signals import post_migrate


def sync_role_permissions(**kwargs) -> None:
    from comptes.permissions import sync_group_permissions

    # Rappels : consultation pour tous dans l'administration ; ils se lancent dans l'application
    sync_group_permissions("qualite", {})


class QualiteConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "qualite"
    verbose_name = "Qualité et traçabilité"

    def ready(self) -> None:
        post_migrate.connect(sync_role_permissions, sender=self)
