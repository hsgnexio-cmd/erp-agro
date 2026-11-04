from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("lots", views.LotViewSet)
router.register("movements", views.StockMovementViewSet)

urlpatterns = router.urls
