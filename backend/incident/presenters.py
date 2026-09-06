from accounts.serializers import present_user


def present_incident(incident):
    analysis = (
        incident.aianalysis_set.order_by("-created_at").first()
        if hasattr(incident, "aianalysis_set")
        else None
    )
    return {
        "id": incident.incident_id,
        "code": incident.incident_code,
        "server_id": incident.server_id_id,
        "server": incident.server_id.name if incident.server_id else "",
        "service_id": incident.service_id,
        "service": incident.service.display_name if incident.service else "",
        "service_name": incident.service.service_name if incident.service else "",
        "environment": incident.server_id.environment if incident.server_id else "",
        "title": incident.title,
        "description": incident.description,
        "category": incident.category,
        "severity": incident.severity,
        "status": incident.status,
        "detected_at": incident.detected_at,
        "acknowledged_at": incident.acknowledged_at,
        "resolved_at": incident.resolved_at,
        "resolution_notes": incident.resolution_notes,
        "assigned_to": present_user(incident.assigned_to),
        "ai_confidence": None if analysis is None else analysis.confidence_score,
    }
