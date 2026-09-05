from django.contrib import admin
from django.urls import include, path

from installer.monitoring_views import MetricsWriteView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/organizations/", include("accounts.organization_urls")),
    path("api/organizations/<uuid:organization_id>/", include("infra_monitor.organization_urls")),
    path("api/monitoring/", include("installer.urls")),
    path("api/internal/monitoring/", include("installer.internal_urls")),
    path("api/", include("infra_monitor.health_urls")),
    path("api/internal/logs/", include("log.internal_urls")),
    path("api/internal/ml/", include("ml_model.internal_urls")),
    path("api/metrics/write", MetricsWriteView.as_view(), name="metrics-write"),
]
