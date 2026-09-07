"""Presenters format sanitize model instances for API responses.

Every API view delegates formatting to a presenter so the response shape is
defined in one place and easily tested in isolation.
"""

from __future__ import annotations


def present_request_log(log):
    """Serialize a ``RequestLog`` instance for the API."""
    return {
        "id": str(log.id),
        "organization_id": str(log.organization_id),
        "server_id": str(log.server_id) if log.server_id else None,
        "timestamp": log.timestamp.isoformat(),
        "source_ip": log.source_ip,
        "method": log.method,
        "path": log.path,
        "query_string": log.query_string,
        "status_code": log.status_code,
        "user_agent": log.user_agent,
        "content_length": log.content_length,
        "response_time_ms": log.response_time_ms,
        "protocol": log.protocol,
        "source": log.source,
        "zone": log.zone,
        "confidence": log.confidence,
        "threat_signals": log.threat_signals,
        "classified_at": log.classified_at.isoformat() if log.classified_at else None,
        "classified_by": log.classified_by,
        "admin_verdict": log.admin_verdict,
        "reviewed_by": str(log.reviewed_by_id) if log.reviewed_by_id else None,
        "reviewed_at": log.reviewed_at.isoformat() if log.reviewed_at else None,
        "created_at": log.created_at.isoformat(),
    }


def present_threat_suggestion(suggestion):
    """Serialize a ``ThreatSuggestion`` instance for the API."""
    return {
        "id": str(suggestion.id),
        "organization_id": str(suggestion.organization_id),
        "ip_address": suggestion.ip_address,
        "trigger_zone": suggestion.trigger_zone,
        "request_count": suggestion.request_count,
        "window_start": suggestion.window_start.isoformat(),
        "window_end": suggestion.window_end.isoformat(),
        "sample_paths": suggestion.sample_paths,
        "top_threat_signals": suggestion.top_threat_signals,
        "gemini_analysis": suggestion.gemini_analysis,
        "status": suggestion.status,
        "resolved_by": str(suggestion.resolved_by_id) if suggestion.resolved_by_id else None,
        "resolved_at": suggestion.resolved_at.isoformat() if suggestion.resolved_at else None,
        "admin_notes": suggestion.admin_notes,
        "created_at": suggestion.created_at.isoformat(),
        "updated_at": suggestion.updated_at.isoformat(),
    }


def present_shield_config(config):
    """Serialize a ``ShieldConfig`` instance for the API."""
    return {
        "id": str(config.id),
        "organization_id": str(config.organization_id),
        "enabled": config.enabled,
        "gemini_escalation": config.gemini_escalation,
        "platform_self_monitor": config.platform_self_monitor,
        "red_suggestion_threshold": config.red_suggestion_threshold,
        "gray_suggestion_threshold": config.gray_suggestion_threshold,
        "suggestion_window_minutes": config.suggestion_window_minutes,
        "notify_on_red": config.notify_on_red,
        "created_at": config.created_at.isoformat(),
        "updated_at": config.updated_at.isoformat(),
    }
