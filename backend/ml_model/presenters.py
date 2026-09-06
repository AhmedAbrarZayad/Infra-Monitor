from accounts.serializers import present_user


def present_anomaly(anomaly):
    return {
        "id": anomaly.detection_id,
        "server_id": anomaly.server_id_id,
        "server_name": anomaly.server_id.name if anomaly.server_id else "",
        "service_id": anomaly.service_id_id,
        "service_name": anomaly.service_id.display_name if anomaly.service_id else "",
        "anomaly_score": anomaly.anomaly_score,
        "confidence_score": anomaly.confidence_score,
        "is_anomaly": anomaly.is_anomaly,
        "feature_values": anomaly.feature_values,
        "model_version": anomaly.model_version,
        "window_started_at": anomaly.window_started_at,
        "window_ended_at": anomaly.window_ended_at,
        "detected_at": anomaly.detected_at,
        "resolved_at": anomaly.resolved_at,
        "resolved_by": anomaly.resolved_by_id,
        "assigned_to": present_user(anomaly.assigned_to),
        "assigned_by": present_user(anomaly.assigned_by),
        "assigned_at": anomaly.assigned_at,
    }
