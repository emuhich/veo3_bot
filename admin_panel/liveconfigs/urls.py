from rest_framework.routers import DefaultRouter

from .views import ConfigRowViewSet

app_name = "config"

router = DefaultRouter()
router.register(prefix="configrow", viewset=ConfigRowViewSet, basename="configrow")
urlpatterns = router.urls
