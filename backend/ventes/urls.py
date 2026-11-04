from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("prices", views.SalePriceViewSet)
router.register("orders", views.CustomerOrderViewSet)
router.register("edi-messages", views.EdiMessageViewSet)
router.register("shipments", views.ShipmentViewSet, basename="shipment")

urlpatterns = [
    path("orderable-articles/", views.OrderableArticlesView.as_view(), name="orderable-articles"),
    *router.urls,
]
