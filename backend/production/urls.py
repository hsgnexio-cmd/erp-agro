from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("orders", views.ProductionOrderViewSet)
router.register("master-plans", views.MasterPlanViewSet)

urlpatterns = [
    path("planning/", views.PlanningView.as_view(), name="production-planning"),
    *router.urls,
]
