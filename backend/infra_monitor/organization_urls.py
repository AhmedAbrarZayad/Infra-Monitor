from django.urls import include, path

urlpatterns = [
    path("", include("dashboard.urls")),
    path("", include("servers.urls")),
    path("", include("alert.urls")),
    path("", include("log.urls")),
    path("", include("incident.urls")),
    path("", include("ml_model.urls")),
]
