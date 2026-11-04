# Charge Celery au démarrage de Django, pour que les tâches soient bien enregistrées.
from .celery import app as celery_app

__all__ = ("celery_app",)
