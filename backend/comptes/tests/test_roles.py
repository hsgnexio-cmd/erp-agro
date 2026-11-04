import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from comptes.roles import Role


@pytest.mark.django_db
def test_les_7_roles_existent():
    noms = set(Group.objects.values_list("name", flat=True))
    assert noms == {
        "admin",
        "direction",
        "acheteur",
        "magasinier",
        "production",
        "qualite",
        "commercial",
    }


@pytest.mark.django_db
def test_un_utilisateur_peut_recevoir_un_role():
    user = get_user_model().objects.create_user(username="claire", password="motdepasse-test")
    user.groups.add(Group.objects.get(name=Role.QUALITE))

    assert user.has_role(Role.QUALITE)
    assert not user.has_role(Role.ACHETEUR)
