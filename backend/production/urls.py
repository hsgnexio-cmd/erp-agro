from django.urls import path

from . import views

urlpatterns = [
    path("productions/", views.ProductionView.as_view(), name="production-create"),
]
