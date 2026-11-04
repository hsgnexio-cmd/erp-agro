import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("erp_agro")
# Lit les réglages CELERY_* dans settings.py
app.config_from_object("django.conf:settings", namespace="CELERY")
# Cherche automatiquement les fichiers tasks.py dans chaque app
app.autodiscover_tasks()


@app.task
def ping() -> str:
    """Tâche de vérification : permet de tester que le worker répond."""
    return "pong"
