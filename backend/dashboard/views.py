from datetime import timedelta

from django.db.models import Count, F, OuterRef, Subquery
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from alert.presenters import present_alert
from common.api import get_organization_membership
from common.authorization import (
    alerts_visible_to,
    anomalies_visible_to,
    incidents_visible_to,
    servers_visible_to,
)
from incident.models import Incident
from incident.presenters import present_incident
from ml_model.presenters import present_anomaly
from servers.models import Servers
from servers.presenters import metric_history
from servers.services import InvalidMetricError


class OverviewView(APIView):
    def get(self, request, organization_id):
        organization, membership = get_organization_membership(request, organization_id)
        servers = servers_visible_to(membership)
        environment = request.query_params.get("environment")
        if environment:
            servers = servers.filter(environment__iexact=environment)
        incidents = incidents_visible_to(membership).exclude(status="RESOLVED")
        alerts = alerts_visible_to(membership).order_by("-triggered_at")[:10]
        latest_service_detection = (
            anomalies_visible_to(membership).filter(
                service_id=OuterRef("service_id"),
            )
            .order_by("-detected_at", "-detection_id")
            .values("detection_id")[:1]
        )
        recent_anomalies = (
            anomalies_visible_to(membership)
            .annotate(latest_detection_id=Subquery(latest_service_detection))
            .filter(
                detection_id=F("latest_detection_id"),
                is_anomaly=True,
                resolved_at__isnull=True,
            )
            .select_related("server_id", "service_id")
            .order_by("-detected_at")[:5]
        )
        return Response(
            {
                "server_count": servers.count(),
                "open_incident_count": incidents.count(),
                "updated_at": timezone.now(),
                "fleet": {
                    state: servers.filter(status=state).count()
                    for state, _ in Servers.Status.choices
                },
                "critical_incidents": [
                    present_incident(item) for item in incidents.filter(severity="CRITICAL")[:5]
                ],
                "high_incidents": [
                    present_incident(item) for item in incidents.filter(severity="HIGH")[:5]
                ],
                # Retained as an empty compatibility field for older clients.
                # Needs Attention is exclusively backed by ML anomalies.
                "attention_items": [],
                "recent_anomalies": [present_anomaly(item) for item in recent_anomalies],
                "alerts": [present_alert(item) for item in alerts],
                "platform_health": [{"component": "api", "status": "HEALTHY"}],
                "telemetry_available": servers.filter(
                    monitoring_connection__last_metric_at__isnull=False
                ).exists(),
            }
        )


class AnalyticsView(APIView):
    def get(self, request, organization_id):
        organization, _ = get_organization_membership(request, organization_id)
        now = timezone.now()
        incidents = Incident.objects.filter(organization=organization)
        resolved = incidents.filter(status="RESOLVED", resolved_at__isnull=False)
        durations = [
            (item.resolved_at - item.detected_at).total_seconds()
            for item in resolved
            if item.resolved_at
        ]
        acknowledge_durations = [
            (item.acknowledged_at - item.detected_at).total_seconds()
            for item in incidents.filter(acknowledged_at__isnull=False)
        ]

        def values(*codes):
            collected = []
            for server in Servers.objects.filter(organization=organization):
                for code in codes:
                    try:
                        collected.extend(metric_history(server, code, limit=100))
                    except InvalidMetricError:
                        continue
            return collected[-100:]

        return Response(
            {
                "available": incidents.exists()
                or Servers.objects.filter(
                    organization=organization, monitoring_connection__last_metric_at__isnull=False
                ).exists(),
                "metrics": {
                    "mtta_seconds": sum(acknowledge_durations) / len(acknowledge_durations)
                    if acknowledge_durations
                    else None,
                    "mttr_seconds": sum(durations) / len(durations) if durations else None,
                    "open": incidents.exclude(status="RESOLVED").count(),
                    "resolved_7d": resolved.filter(
                        resolved_at__gte=now - timedelta(days=7)
                    ).count(),
                },
                "series": {
                    "cpu": values("cpu_r"),
                    "memory": values("mem_u"),
                    "latency": values("latency", "request_latency"),
                    "frequency": [],
                    "opened": [],
                    "resolved": [],
                    "uptime": values("uptime"),
                },
                "categories": dict(
                    incidents.values_list("category").annotate(c=Count("incident_id"))
                ),
                "servers": dict(
                    incidents.filter(server_id__isnull=False)
                    .values_list("server_id__name")
                    .annotate(c=Count("incident_id"))
                ),
                "insights": [],
            }
        )
