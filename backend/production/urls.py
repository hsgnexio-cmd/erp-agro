from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("orders", views.ProductionOrderViewSet)
router.register("master-plans", views.MasterPlanViewSet)
router.register("line-stops", views.LineStopViewSet)

urlpatterns = [
    path("planning/", views.PlanningView.as_view(), name="production-planning"),
    path("oee/", views.OeeView.as_view(), name="production-oee"),
    *router.urls,
]
