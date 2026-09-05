from accounts.serializers import present_user


def present_alert(alert):
    return {
        "id": alert.alert_id,
        "server_id": alert.server_id_id,
        "service_id": alert.service_id_id,
        "detection_id": alert.detection_id_id,
        "title": alert.title,
        "description": alert.description,
        "category": alert.category,
        "severity": alert.severity,
        "state": alert.state,
        "fingerprint": alert.fingerprint,
        "triggered_at": alert.triggered_at,
        "acknowledged_at": alert.acknowledged_at,
        "cleared_at": alert.cleared_at,
        "acknowledged_by": present_user(alert.acknowledged_by),
    }
