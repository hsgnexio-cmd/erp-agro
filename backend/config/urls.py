from django.contrib import admin
from django.urls import path

from .views import health

admin.site.site_header = "ERP Brévanne Traiteur"
admin.site.site_title = "ERP Brévanne Traiteur"
admin.site.index_title = "Administration"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
]
