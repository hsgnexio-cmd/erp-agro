from django.apps import AppConfig
from django.db.models.signals import post_migrate


class ReferentielConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "referentiel"
    verbose_name = "Référentiel"

    def ready(self) -> None:
        from .permissions import sync_role_permissions

        post_migrate.connect(sync_role_permissions, sender=self)
