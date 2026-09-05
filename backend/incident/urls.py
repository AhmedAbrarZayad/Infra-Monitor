from django.urls import path

from incident.views import (
    IncidentAcknowledgeView,
    IncidentAlertsView,
    IncidentAssignView,
    IncidentBulkAcknowledgeView,
    IncidentDetailView,
    IncidentEvidenceView,
    IncidentFeedbackView,
    IncidentListView,
    IncidentSelfAssignView,
    IncidentStatusView,
    IncidentUpdatesView,
)

app_name = "incidents"
urlpatterns = [
    path("incidents/", IncidentListView.as_view(), name="list"),
    path(
        "incidents/bulk-acknowledge/",
        IncidentBulkAcknowledgeView.as_view(),
        name="bulk-acknowledge",
    ),
    path("incidents/<uuid:incident_id>/", IncidentDetailView.as_view(), name="detail"),
    path(
        "incidents/<uuid:incident_id>/acknowledge/",
        IncidentAcknowledgeView.as_view(),
        name="acknowledge",
    ),
    path(
        "incidents/<uuid:incident_id>/assignment/", IncidentAssignView.as_view(), name="assignment"
    ),
    path(
        "incidents/<uuid:incident_id>/assign-to-me/",
        IncidentSelfAssignView.as_view(),
        name="self-assign",
    ),
    path("incidents/<uuid:incident_id>/status/", IncidentStatusView.as_view(), name="status"),
    path("incidents/<uuid:incident_id>/updates/", IncidentUpdatesView.as_view(), name="updates"),
    path("incidents/<uuid:incident_id>/feedback/", IncidentFeedbackView.as_view(), name="feedback"),
    path("incidents/<uuid:incident_id>/alerts/", IncidentAlertsView.as_view(), name="alerts"),
    path("incidents/<uuid:incident_id>/evidence/", IncidentEvidenceView.as_view(), name="evidence"),
]
