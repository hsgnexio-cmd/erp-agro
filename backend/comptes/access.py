"""Qui voit quoi : matrice d'accès en lecture par domaine (principe du moindre privilège).

Chaque rôle consulte les données utiles à son métier, en plus de celles qu'il modifie. Les
droits d'écriture restent définis vue par vue (`write_roles`) ; un rôle qui modifie un domaine
le voit toujours. La matrice est appliquée par le serveur (WriteRolesPermission, attribut
`read_area` des vues) : un rôle non autorisé reçoit un refus, les données ne sont pas
seulement cachées à l'écran. Le menu de l'application suit la même matrice
(`frontend/src/auth/roles.ts`).
"""

from .permissions import has_any_role
from .roles import Role

ADMIN, DIRECTION = Role.ADMIN, Role.DIRECTION
ACHETEUR, MAGASINIER, PRODUCTION = Role.ACHETEUR, Role.MAGASINIER, Role.PRODUCTION
QUALITE, COMMERCIAL = Role.QUALITE, Role.COMMERCIAL

# None = tous les rôles
READ_AREAS: dict[str, list[Role] | None] = {
    # Référentiel, stocks et lots, traçabilité et rappels : utiles à tous (un rappel concerne
    # toute l'entreprise)
    "referentiel": None,
    "stocks": None,
    "qualite": None,
    # Commandes fournisseurs et réceptions : achats, quai, contrôle qualité, approvisionnement
    "achats": [ADMIN, DIRECTION, ACHETEUR, MAGASINIER, PRODUCTION, QUALITE],
    # Prix d'achat (tarifs, montants des commandes) : achats et direction seulement
    "prix_achat": [ADMIN, DIRECTION, ACHETEUR],
    # Calcul des besoins (MRP) : achats, et la production qui en fournit le plan
    "mrp": [ADMIN, DIRECTION, ACHETEUR, PRODUCTION],
    # OF, planning, plan de production, TRS : production, qualité (libération), achats (MRP)
    "production": [ADMIN, DIRECTION, PRODUCTION, QUALITE, ACHETEUR],
    # Commandes clients, EDI, expéditions, taux de service : ventes, quai, qualité (clients)
    "ventes": [ADMIN, DIRECTION, COMMERCIAL, MAGASINIER, QUALITE],
    # Prix de vente (tarifs, montants des commandes clients) : ventes et direction seulement
    "prix_vente": [ADMIN, DIRECTION, COMMERCIAL],
    # Prévisions de vente : ventes, production (plan), achats (MRP)
    "previsions": [ADMIN, DIRECTION, COMMERCIAL, PRODUCTION, ACHETEUR],
    # Tableau de bord : chaque rôle y voit les indicateurs de son métier (DASHBOARD_INDICATORS)
    "pilotage": None,
}

# Indicateurs du tableau de bord de chaque rôle (codes de pilotage/indicators.py). L'admin et la
# direction voient tout, avec les montants en euros ; un utilisateur à plusieurs rôles voit la
# réunion de leurs indicateurs.
DASHBOARD_INDICATORS: dict[Role, list[str]] = {
    QUALITE: ["reception_compliance", "traceability", "markdown"],
    PRODUCTION: ["material_yield", "oee", "material_coverage"],
    ACHETEUR: ["material_coverage", "reception_compliance"],
    COMMERCIAL: ["service_rate", "forecast_accuracy"],
    MAGASINIER: ["service_rate", "finished_coverage"],
}

# Montants en euros (chiffre d'affaires, démarque, stocks valorisés) : direction seulement
AMOUNTS_ROLES = [ADMIN, DIRECTION]


def can_read(user, area: str) -> bool:
    roles = READ_AREAS[area]
    return user.is_authenticated and (roles is None or has_any_role(user, roles))


def readable_areas(user) -> list[str]:
    """Domaines que l'utilisateur peut consulter (renvoyés au front-end pour son menu)."""
    return [area for area in READ_AREAS if can_read(user, area)]


def dashboard_indicators(user) -> set[str] | None:
    """Codes des indicateurs que l'utilisateur voit au tableau de bord (None = tous)."""
    if has_any_role(user, AMOUNTS_ROLES):
        return None
    codes = set()
    for role, role_codes in DASHBOARD_INDICATORS.items():
        if has_any_role(user, [role]):
            codes.update(role_codes)
    return codes


def can_see_amounts(user) -> bool:
    """Vrai si l'utilisateur voit les montants en euros du tableau de bord."""
    return has_any_role(user, AMOUNTS_ROLES)


def mask_prices(data: dict, request, area: str, fields: tuple[str, ...], line_fields=()) -> dict:
    """Retire les prix d'une réponse (commande et ses lignes) pour un rôle qui ne les voit pas."""
    if request is None or can_read(request.user, area):
        return data
    for name in fields:
        if name in data:
            data[name] = None
    for line in data.get("lines", []) or []:
        for name in line_fields:
            if name in line:
                line[name] = None
    return data
