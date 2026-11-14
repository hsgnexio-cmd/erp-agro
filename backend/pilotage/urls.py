from django.urls import path

from . import views

urlpatterns = [
    path("indicators/", views.IndicatorsView.as_view(), name="indicators"),
    path("search/", views.SearchView.as_view(), name="search"),
    path("indicators/export/", views.IndicatorsExportView.as_view(), name="indicators-export"),
]
