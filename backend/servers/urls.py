from django.urls import path

from servers.views import (
    ServerDetailView,
    ServerHealthView,
    ServerListView,
    ServerMetricRangeView,
    ServiceDetailView,
    ServiceHealthView,
    ServiceListView,
    ServiceAdminAssignmentView,
    ServiceAdminAssignmentHistoryView,
    ServiceMetricRangeView,
)

app_name = "servers"

urlpatterns = [
    path("servers/", ServerListView.as_view(), name="list"),
    path("servers/<uuid:server_id>/", ServerDetailView.as_view(), name="detail"),
    path("servers/<uuid:server_id>/health/", ServerHealthView.as_view(), name="health"),
    path("servers/<uuid:server_id>/metrics/", ServerMetricRangeView.as_view(), name="metrics"),
    path("servers/<uuid:server_id>/services/", ServiceListView.as_view(), name="service-list"),
    path("services/<uuid:service_id>/", ServiceDetailView.as_view(), name="service-detail"),
    path(
        "services/<uuid:service_id>/admins/",
        ServiceAdminAssignmentView.as_view(),
        name="service-admins",
    ),
    path(
        "services/<uuid:service_id>/admins/history/",
        ServiceAdminAssignmentHistoryView.as_view(),
        name="service-admin-history",
    ),
    path("services/<uuid:service_id>/health/", ServiceHealthView.as_view(), name="service-health"),
    path(
        "services/<uuid:service_id>/metrics/",
        ServiceMetricRangeView.as_view(),
        name="service-metrics",
    ),
]
