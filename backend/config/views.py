from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request: Request) -> Response:
    """Indique si le back-end fonctionne et s'il arrive à joindre la base de données."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        database = "ok"
    except Exception:
        database = "erreur"
    status_code = 200 if database == "ok" else 503
    return Response(
        {"status": "ok" if database == "ok" else "erreur", "database": database},
        status=status_code,
    )
