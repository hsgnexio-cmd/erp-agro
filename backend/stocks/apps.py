from django.apps import AppConfig
from django.db.models.signals import post_migrate


def sync_role_permissions(**kwargs) -> None:
    from comptes.permissions import sync_group_permissions

    # Lots et mouvements : consultation pour tous, jamais de saisie manuelle
    sync_group_permissions("stocks", {})


class StocksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "stocks"
    verbose_name = "Stocks et lots"

    def ready(self) -> None:
        post_migrate.connect(sync_role_permissions, sender=self)
