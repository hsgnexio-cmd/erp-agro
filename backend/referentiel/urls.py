from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("sites", views.SiteViewSet)
router.register("locations", views.LocationViewSet)
router.register("families", views.ProductFamilyViewSet)
router.register("categories", views.MaterialCategoryViewSet)
router.register("allergens", views.AllergenViewSet)
router.register("customers", views.CustomerViewSet)
router.register("customer-warehouses", views.CustomerWarehouseViewSet)
router.register("recipes", views.RecipeViewSet)
router.register("articles", views.ArticleViewSet)
router.register("boms", views.BillOfMaterialsViewSet)
router.register("bom-lines", views.BOMLineViewSet)
router.register("suppliers", views.SupplierViewSet)
router.register("supplier-articles", views.SupplierArticleViewSet)
router.register("production-lines", views.ProductionLineViewSet)

urlpatterns = router.urls
