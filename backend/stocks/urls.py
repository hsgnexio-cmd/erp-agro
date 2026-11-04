from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("lots", views.LotViewSet)
router.register("movements", views.StockMovementViewSet)

urlpatterns = [
    path("fefo/", views.FefoView.as_view(), name="fefo"),
    path("summary/", views.StockSummaryView.as_view(), name="stock-summary"),
    *router.urls,
]
