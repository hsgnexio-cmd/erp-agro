from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("recalls", views.RecallViewSet)

urlpatterns = [
    path("traceability/", views.TraceabilityView.as_view(), name="traceability"),
    path("recall-simulation/", views.RecallSimulationView.as_view(), name="recall-simulation"),
    path("allergens/", views.AllergensView.as_view(), name="allergens"),
    *router.urls,
]
