from django.contrib import admin
from django.urls import include, path

from .views import health

admin.site.site_header = "ERP Brévanne Traiteur"
admin.site.site_title = "ERP Brévanne Traiteur"
admin.site.index_title = "Administration"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/auth/", include("comptes.urls")),
    path("api/referentiel/", include("referentiel.urls")),
    path("api/achats/", include("achats.urls")),
    path("api/stocks/", include("stocks.urls")),
    path("api/production/", include("production.urls")),
    path("api/ventes/", include("ventes.urls")),
    path("api/qualite/", include("qualite.urls")),
    path("api/pilotage/", include("pilotage.urls")),
]
