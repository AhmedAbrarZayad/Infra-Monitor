from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from alert.models import Alert
from incident.models import Incident, IncidentAlert, IncidentUpdate
from servers.models import MonitoringConnection, Servers, Service


def _fingerprint(service):
    return f"service-offline:{service.service_id}"


def _incident_code(service):
    return f"SVC-{service.service_id.hex[:16]}-OFFLINE"


def _open_failure(service, now):
    alert, _ = Alert.objects.get_or_create(
        organization=service.server_id.organization,
        fingerprint=_fingerprint(service),
        state__in=[Alert.State.ACTIVE, Alert.State.ACKNOWLEDGED],
        defaults={
            "server_id": service.server_id,
            "service_id": service,
            "title": f"Service offline: {service.display_name}",
            "description": "Service telemetry stopped while the server collector remained healthy.",
            "category": "SERVICE_OFFLINE",
            "severity": Alert.Severity.CRITICAL,
            "triggered_at": now,
        },
    )
    incident, created = Incident.objects.get_or_create(
        organization=service.server_id.organization,
        incident_code=_incident_code(service),
        defaults={
            "server_id": service.server_id,
            "title": f"Service offline: {service.display_name}",
            "description": "A monitored service stopped reporting while its collector remained available.",
            "category": "SERVICE_OFFLINE",
            "severity": Incident.Severity.CRITICAL,
            "detected_at": now,
        },
    )
    if not created and incident.status == Incident.Status.RESOLVED:
        old_status = incident.status
        incident.status = Incident.Status.NEW
        incident.detected_at = now
        incident.resolved_at = None
        incident.resolution_notes = ""
        incident.save(update_fields=["status", "detected_at", "resolved_at", "resolution_notes"])
        IncidentUpdate.objects.create(
            incident_id=incident,
            action="SERVICE_OFFLINE_REOPENED",
            old_status=old_status,
            new_status=incident.status,
        )
    IncidentAlert.objects.get_or_create(incident_id=incident, alert_id=alert)


def _resolve_failure(service, now):
    alerts = Alert.objects.filter(
        organization=service.server_id.organization,
        fingerprint=_fingerprint(service),
        state__in=[Alert.State.ACTIVE, Alert.State.ACKNOWLEDGED],
    )
    alerts.update(state=Alert.State.RESOLVED, cleared_at=now)
    incident = Incident.objects.filter(
        organization=service.server_id.organization,
        incident_code=_incident_code(service),
    ).first()
    if incident is not None and incident.status != Incident.Status.RESOLVED:
        old_status = incident.status
        incident.status = Incident.Status.RESOLVED
        incident.resolved_at = now
        incident.resolution_notes = "Service telemetry recovered."
        incident.save(update_fields=["status", "resolved_at", "resolution_notes"])
        IncidentUpdate.objects.create(
            incident_id=incident,
            action="SERVICE_RECOVERED",
            old_status=old_status,
            new_status=incident.status,
        )


def desired_service_state(service, now=None):
    now = now or timezone.now()
    stale_after = timedelta(seconds=settings.SERVICE_STALE_AFTER_SECONDS)
    offline_after = timedelta(seconds=settings.SERVICE_OFFLINE_AFTER_SECONDS)
    reference = service.last_reported_at or service.created_at

    try:
        connection = service.server_id.monitoring_connection
    except MonitoringConnection.DoesNotExist:
        return Servers.Status.UNKNOWN, "monitoring_not_configured"

    if connection.status == MonitoringConnection.Status.DISCONNECTED:
        return Servers.Status.STALE, "monitoring_disconnected"
    if service.consecutive_failure_observations >= 2:
        return Servers.Status.OFFLINE, "application_unreachable"
    if service.consecutive_failure_observations == 1:
        return Servers.Status.WARNING, "application_unreachable"
    if reference >= now - stale_after:
        return Servers.Status.HEALTHY, "telemetry_received"

    collector_recent = (
        connection.last_metric_at is not None
        and connection.last_metric_at >= now - stale_after
        and connection.ingestion_health == MonitoringConnection.IngestionHealth.HEALTHY
    )
    if not collector_recent:
        return Servers.Status.STALE, "collector_unavailable"
    if reference < now - offline_after:
        return Servers.Status.OFFLINE, "service_telemetry_timeout"
    return Servers.Status.STALE, "service_telemetry_delayed"


def evaluate_service(service_id, now=None):
    now = now or timezone.now()
    with transaction.atomic():
        service = (
            Service.objects.select_for_update()
            .select_related("server_id__organization", "server_id__monitoring_connection")
            .get(service_id=service_id)
        )
        previous = service.status
        desired, reason = desired_service_state(service, now)
        changed = previous != desired
        service.status = desired
        service.lifecycle_reason = reason
        update_fields = ["status", "lifecycle_reason"]
        if changed:
            service.status_changed_at = now
            update_fields.append("status_changed_at")
        service.save(update_fields=update_fields)

        if desired == Servers.Status.OFFLINE:
            _open_failure(service, now)
        elif previous == Servers.Status.OFFLINE and desired == Servers.Status.HEALTHY:
            _resolve_failure(service, now)
        return desired, reason, changed


def record_explicit_health(service_id, healthy, now=None):
    now = now or timezone.now()
    with transaction.atomic():
        service = (
            Service.objects.select_for_update()
            .select_related("server_id__organization")
            .get(service_id=service_id)
        )
        previous = service.status
        if healthy:
            service.consecutive_failure_observations = 0
            desired = Servers.Status.HEALTHY
            reason = "application_up"
        else:
            service.consecutive_failure_observations = min(
                service.consecutive_failure_observations + 1,
                32767,
            )
            desired = (
                Servers.Status.OFFLINE
                if service.consecutive_failure_observations >= 2
                else Servers.Status.WARNING
            )
            reason = "application_unreachable"
        changed = previous != desired
        service.status = desired
        service.lifecycle_reason = reason
        update_fields = [
            "status",
            "lifecycle_reason",
            "consecutive_failure_observations",
        ]
        if changed:
            service.status_changed_at = now
            update_fields.append("status_changed_at")
        service.save(update_fields=update_fields)
        if desired == Servers.Status.OFFLINE:
            _open_failure(service, now)
        elif healthy and previous == Servers.Status.OFFLINE:
            _resolve_failure(service, now)
        return desired, reason, changed


def evaluate_all_services(now=None):
    now = now or timezone.now()
    service_ids = list(Service.objects.values_list("service_id", flat=True))
    counts = {"evaluated": 0, "changed": 0, "offline": 0}
    for service_id in service_ids:
        state, _, changed = evaluate_service(service_id, now=now)
        counts["evaluated"] += 1
        counts["changed"] += int(changed)
        counts["offline"] += int(state == Servers.Status.OFFLINE)
    return counts
