from django.apps import AppConfig
from django.db.models.signals import post_migrate


def sync_role_permissions(**kwargs) -> None:
    from comptes.permissions import sync_group_permissions

    # Tout se saisit dans l'application (règles appliquées) : consultation seule dans
    # l'administration, pour tous les rôles
    sync_group_permissions("previsions", {})


class PrevisionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "previsions"
    verbose_name = "Prévisions"

    def ready(self) -> None:
        post_migrate.connect(sync_role_permissions, sender=self)
