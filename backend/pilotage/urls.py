from django.urls import path

from . import views

urlpatterns = [
    path("indicators/", views.IndicatorsView.as_view(), name="indicators"),
]
