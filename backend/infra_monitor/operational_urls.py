from django.urls import path
from .operational_views import *

urlpatterns = [
 path("overview/",OverviewView.as_view()), path("analytics/",AnalyticsView.as_view()),
 path("servers/",ServerListView.as_view()), path("servers/<uuid:server_id>/",ServerDetailView.as_view()),
 path("servers/<uuid:server_id>/health/",ServerHealthView.as_view()), path("servers/<uuid:server_id>/metrics/",MetricRangeView.as_view()),
 path("servers/<uuid:server_id>/services/",ServiceListView.as_view()), path("services/<uuid:service_id>/",ServiceDetailView.as_view()),
 path("services/<uuid:service_id>/health/",ServiceHealthView.as_view()), path("services/<uuid:service_id>/metrics/",type("ServiceMetricView",(MetricRangeView,),{"service_scoped":True}).as_view()),
 path("alerts/",AlertListView.as_view()), path("alerts/<uuid:alert_id>/",AlertDetailView.as_view()),
 path("alerts/<uuid:alert_id>/acknowledge/",AlertActionView.as_view()), path("alerts/<uuid:alert_id>/resolve/",type("ResolveAlertView",(AlertActionView,),{"resolve":True}).as_view()),
 path("logs/",LogListView.as_view()), path("logs/<uuid:log_id>/",LogDetailView.as_view()),
 path("incidents/",IncidentListView.as_view()), path("incidents/bulk-acknowledge/",IncidentBulkAcknowledgeView.as_view()),
 path("incidents/<uuid:incident_id>/",IncidentDetailView.as_view()), path("incidents/<uuid:incident_id>/acknowledge/",IncidentAcknowledgeView.as_view()),
 path("incidents/<uuid:incident_id>/assignment/",IncidentAssignView.as_view()), path("incidents/<uuid:incident_id>/assign-to-me/",type("SelfAssignView",(IncidentAssignView,),{"self_assign":True}).as_view()),
 path("incidents/<uuid:incident_id>/status/",IncidentStatusView.as_view()), path("incidents/<uuid:incident_id>/updates/",IncidentUpdatesView.as_view()),
 path("incidents/<uuid:incident_id>/feedback/",IncidentFeedbackView.as_view()), path("incidents/<uuid:incident_id>/alerts/",IncidentAlertsView.as_view()), path("incidents/<uuid:incident_id>/evidence/",IncidentEvidenceView.as_view()),
 path("anomalies/",AnomalyListView.as_view()), path("anomalies/<uuid:detection_id>/",AnomalyDetailView.as_view()),
]
