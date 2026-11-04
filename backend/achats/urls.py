from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("prices", views.SupplierPriceViewSet)
router.register("orders", views.PurchaseOrderViewSet)
router.register("receptions", views.ReceptionViewSet)

urlpatterns = [
    path("catalog/", views.SupplierCatalogView.as_view(), name="supplier-catalog"),
    *router.urls,
]
