from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("versions", views.ForecastVersionViewSet)
router.register("promotions", views.PromotionViewSet)
router.register("adjustments", views.ForecastAdjustmentViewSet)

urlpatterns = [
    path("forecast/", views.ForecastView.as_view(), name="forecast"),
    path("accuracy/", views.AccuracyView.as_view(), name="forecast-accuracy"),
    *router.urls,
]
