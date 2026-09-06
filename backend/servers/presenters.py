from alert.models import Alert
from servers.services import VictoriaMetricsQueryAdapter


def latest_metric(server, code, service=None):
    return VictoriaMetricsQueryAdapter().latest(server=server, code=code, service=service)


def metric_value(server, code, service=None):
    item = latest_metric(server, code, service)["point"]
    if item is None:
        return None
    return {
        "value": item["value"],
        "unit": item["unit"],
        "recorded_at": item["recorded_at"],
        "labels": item["labels"],
    }


def metric_history(server, code, service=None, limit=30):
    result = VictoriaMetricsQueryAdapter().range(server=server, code=code, service=service)
    return [point["value"] for point in result["points"][-limit:]]


def present_server(server, membership=None):
    active_states = ["ACTIVE", "ACKNOWLEDGED"]
    restricted = membership is not None and membership.role != "OWNER"
    if restricted:
        from common.authorization import alerts_visible_to, services_visible_to

        alert_count = alerts_visible_to(membership).filter(
            server_id=server, state__in=active_states
        ).count()
        service_count = services_visible_to(membership).filter(server_id=server).count()
        metrics = {}
        cpu_history = []
    else:
        alert_count = Alert.objects.filter(
            organization=server.organization,
            server_id=server,
            state__in=active_states,
        ).count()
        service_count = server.services.count()
        metrics = {code: metric_value(server, code) for code in ["cpu_r", "mem_u", "disk_u"]}
        cpu_history = metric_history(server, "cpu_r")
    return {
        "id": server.server_id,
        "name": server.name,
        "host_name": server.host_name,
        "environment": server.environment,
        "os_type": server.os_type,
        "status": server.status,
        "last_seen_at": server.last_seen_at,
        "registered_at": server.registered_at,
        "alert_count": alert_count,
        "metrics": metrics,
        "service_count": service_count,
        "cpu_history": cpu_history,
    }


def present_service(service, membership=None):
    if membership is None or membership.role == "OWNER":
        alerts = Alert.objects.filter(
            organization=service.server_id.organization,
            service_id=service,
            state__in=["ACTIVE", "ACKNOWLEDGED"],
        )
    else:
        from common.authorization import alerts_visible_to

        alerts = alerts_visible_to(membership).filter(
            service_id=service, state__in=["ACTIVE", "ACKNOWLEDGED"]
        )
    return {
        "id": service.service_id,
        "server_id": service.server_id_id,
        "service_name": service.service_name,
        "display_name": service.display_name,
        "status": service.status,
        "status_changed_at": service.status_changed_at,
        "lifecycle_reason": service.lifecycle_reason,
        "consecutive_failure_observations": service.consecutive_failure_observations,
        "port": service.port,
        "last_reported_at": service.last_reported_at,
        "alert_count": alerts.count(),
    }
