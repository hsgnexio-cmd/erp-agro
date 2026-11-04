from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    """Renvoie une erreur 400 lisible quand une règle métier refuse une opération.

    Les règles sont vérifiées dans les modèles (ValidationError de Django) :
    on les convertit au format de l'API au lieu de laisser une erreur 500.
    """
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "error_dict"):
            exc = ValidationError(exc.message_dict)
        else:
            exc = ValidationError({"non_field_errors": exc.messages})
    return drf_exception_handler(exc, context)
