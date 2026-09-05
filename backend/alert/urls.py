from django.urls import path

from alert.views import AlertAcknowledgeView, AlertDetailView, AlertListView, AlertResolveView

app_name = "alerts"

urlpatterns = [
    path("alerts/", AlertListView.as_view(), name="list"),
    path("alerts/<uuid:alert_id>/", AlertDetailView.as_view(), name="detail"),
    path("alerts/<uuid:alert_id>/acknowledge/", AlertAcknowledgeView.as_view(), name="acknowledge"),
    path("alerts/<uuid:alert_id>/resolve/", AlertResolveView.as_view(), name="resolve"),
]
