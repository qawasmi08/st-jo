from django.urls import include, path
from rest_framework.routers import DefaultRouter

from shop import views as shop_views

router = DefaultRouter()
router.register(r"products", shop_views.ProductViewSet, basename="product")
router.register(r"categories", shop_views.CategoryViewSet, basename="category")
router.register(r"brands", shop_views.BrandViewSet, basename="brand")
router.register(r"standard-orders", shop_views.StandardOrderViewSet, basename="standard-order")
router.register(r"custom-orders", shop_views.CustomOrderViewSet, basename="custom-order")

urlpatterns = [
    path("", include(router.urls)),
    path("uploads/image/", shop_views.ProductImageUploadView.as_view(), name="product-image-upload"),
]
