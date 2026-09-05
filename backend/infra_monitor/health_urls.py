from django.urls import path

from infra_monitor.health_views import DependencyHealthView, LiveView, ReadyView, WorkerHealthView

urlpatterns = [
    path("health/live/", LiveView.as_view(), name="health-live"),
    path("health/ready/", ReadyView.as_view(), name="health-ready"),
    path(
        "internal/health/dependencies/", DependencyHealthView.as_view(), name="health-dependencies"
    ),
    path("internal/health/workers/", WorkerHealthView.as_view(), name="health-workers"),
]
