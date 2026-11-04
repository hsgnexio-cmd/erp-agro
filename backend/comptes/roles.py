"""Les 7 rôles de l'ERP (voir CLAUDE.md, section 9).

Chaque rôle correspond à un groupe Django. Les droits précis de chaque groupe
seront ajoutés module par module, au fil des phases.
"""

from django.db import models


class Role(models.TextChoices):
    ADMIN = "admin", "Administrateur"
    DIRECTION = "direction", "Direction"
    ACHETEUR = "acheteur", "Acheteur"
    MAGASINIER = "magasinier", "Magasinier"
    PRODUCTION = "production", "Production"
    QUALITE = "qualite", "Qualité"
    COMMERCIAL = "commercial", "Commercial"
