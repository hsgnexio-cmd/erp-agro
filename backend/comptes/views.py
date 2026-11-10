"""Connexion et déconnexion pour l'application React (session Django)."""

from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


def serialize_user(user) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "job_title": user.job_title,
        "last_name": user.last_name,
        "is_superuser": user.is_superuser,
        "roles": sorted(user.groups.values_list("name", flat=True)),
    }


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """Dépose le cookie de sécurité CSRF, nécessaire avant de se connecter."""

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response({"detail": "ok"})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        user = authenticate(
            request,
            username=request.data.get("username", ""),
            password=request.data.get("password", ""),
        )
        if user is None:
            return Response(
                {"detail": "Identifiant ou mot de passe incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        login(request, user)
        return Response(serialize_user(user))


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """Renvoie l'utilisateur connecté et ses rôles."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response(serialize_user(request.user))
