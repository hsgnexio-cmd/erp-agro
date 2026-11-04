from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("lots", views.LotViewSet)
router.register("movements", views.StockMovementViewSet)
router.register("temperatures", views.TemperatureReadingViewSet)
router.register("inventories", views.InventoryViewSet)
router.register("alerts", views.AlertViewSet)

urlpatterns = [
    path("fefo/", views.FefoView.as_view(), name="fefo"),
    path("summary/", views.StockSummaryView.as_view(), name="stock-summary"),
    *router.urls,
]
