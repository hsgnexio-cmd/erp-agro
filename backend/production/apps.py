from django.apps import AppConfig
from django.db.models.signals import post_migrate


def sync_role_permissions(**kwargs) -> None:
    from comptes.permissions import sync_group_permissions

    # OF : consultation pour tous dans l'administration ; ils se gèrent dans l'application
    sync_group_permissions("production", {})


class ProductionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "production"
    verbose_name = "Production"

    def ready(self) -> None:
        post_migrate.connect(sync_role_permissions, sender=self)
