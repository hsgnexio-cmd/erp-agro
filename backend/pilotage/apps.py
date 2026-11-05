from django.apps import AppConfig
from django.db.models.signals import post_migrate


class PilotageConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pilotage"
    verbose_name = "Pilotage"

    def ready(self) -> None:
        from .bi_access import refresh_grants

        post_migrate.connect(refresh_grants, sender=self)
