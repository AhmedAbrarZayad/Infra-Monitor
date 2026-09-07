"""Organization-scoped views for the Request Shield feature.

These are called by the Flutter frontend and require JWT authentication.
All endpoints are nested under /api/organizations/<org_id>/request-shield/.
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.api import get_organization_membership, paginated_response
from sanitize.models import RequestLog, ShieldConfig, ThreatSuggestion
from sanitize.presenters import (
    present_request_log,
    present_shield_config,
    present_threat_suggestion,
)
from sanitize.serializers import (
    AdminVerdictSerializer,
    ShieldConfigUpdateSerializer,
    ThreatSuggestionActionSerializer,
)
from sanitize.services import (
    top_offending_ips,
    zone_distribution,
    zone_trend,
)


# ── Analytics ───────────────────────────────────────────────────────


class ShieldAnalyticsView(APIView):
    """Aggregate analytics for the Request Shield dashboard."""

    def get(self, request, organization_id):
        organization, membership = get_organization_membership(request, organization_id)

        hours = int(request.query_params.get("hours", "24"))
        hours = min(max(hours, 1), 720)  # Clamp to 1h–30d
        source = request.query_params.get("source")  # EXTERNAL | PLATFORM | None (all)

        dist = zone_distribution(organization.id, hours=hours)
        top_ips = top_offending_ips(organization.id, hours=hours, limit=10)
        trend = zone_trend(organization.id, hours=hours)

        # Per-source counts for the dual-panel view
        base_qs = RequestLog.objects.filter(
            organization=organization,
            timestamp__gte=timezone.now() - timezone.timedelta(hours=hours),
        )
        if source:
            base_qs = base_qs.filter(source=source.upper())

        pending_suggestions = ThreatSuggestion.objects.filter(
            organization=organization,
            status=ThreatSuggestion.Status.PENDING,
        ).count()

        config = ShieldConfig.objects.filter(organization=organization).first()

        return Response(
            {
                "zone_distribution": dist,
                "top_offending_ips": top_ips,
                "zone_trend": [
                    {
                        "bucket": entry["bucket"].isoformat(),
                        "zone": entry["zone"],
                        "count": entry["count"],
                    }
                    for entry in trend
                ],
                "total_requests": base_qs.count(),
                "pending_suggestions": pending_suggestions,
                "shield_enabled": config.enabled if config else False,
                "hours": hours,
            }
        )


# ── Request log listing ────────────────────────────────────────────


class RequestLogListView(APIView):
    """Paginated list of request logs with zone/source/IP filtering."""

    def get(self, request, organization_id):
        organization, membership = get_organization_membership(request, organization_id)
        qs = RequestLog.objects.filter(organization=organization)

        # Filters
        zone = request.query_params.get("zone")
        if zone:
            qs = qs.filter(zone=zone.upper())
        source = request.query_params.get("source")
        if source:
            qs = qs.filter(source=source.upper())
        ip = request.query_params.get("ip")
        if ip:
            qs = qs.filter(source_ip=ip)
        method = request.query_params.get("method")
        if method:
            qs = qs.filter(method=method.upper())
        path_contains = request.query_params.get("path")
        if path_contains:
            qs = qs.filter(path__icontains=path_contains)

        qs = qs.order_by("-timestamp")
        return paginated_response(request, qs, present_request_log)


class RequestLogDetailView(APIView):
    """Retrieve a single request log by ID."""

    def get(self, request, organization_id, log_id):
        organization, membership = get_organization_membership(request, organization_id)
        log = get_object_or_404(RequestLog, id=log_id, organization=organization)
        return Response(present_request_log(log))


# ── Admin verdict ──────────────────────────────────────────────────


class RequestLogVerdictView(APIView):
    """Admin marks a request as confirmed_safe or confirmed_threat."""

    def post(self, request, organization_id, log_id):
        organization, membership = get_organization_membership(request, organization_id)
        log = get_object_or_404(RequestLog, id=log_id, organization=organization)

        serializer = AdminVerdictSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        log.admin_verdict = serializer.validated_data["verdict"]
        log.reviewed_by = request.user
        log.reviewed_at = timezone.now()
        log.save(update_fields=["admin_verdict", "reviewed_by", "reviewed_at"])

        return Response(present_request_log(log))


# ── Threat suggestions ─────────────────────────────────────────────


class ThreatSuggestionListView(APIView):
    """List threat suggestions for the organization."""

    def get(self, request, organization_id):
        organization, membership = get_organization_membership(request, organization_id)
        qs = ThreatSuggestion.objects.filter(organization=organization)

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        qs = qs.order_by("-created_at")
        return paginated_response(request, qs, present_threat_suggestion)


class ThreatSuggestionActionView(APIView):
    """Admin accepts or dismisses a threat suggestion."""

    def post(self, request, organization_id, suggestion_id):
        organization, membership = get_organization_membership(request, organization_id)
        suggestion = get_object_or_404(
            ThreatSuggestion,
            id=suggestion_id,
            organization=organization,
        )

        serializer = ThreatSuggestionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data["action"] == "accept":
            suggestion.status = ThreatSuggestion.Status.ACCEPTED
        else:
            suggestion.status = ThreatSuggestion.Status.DISMISSED

        suggestion.resolved_by = request.user
        suggestion.resolved_at = timezone.now()
        suggestion.admin_notes = data.get("notes", "")
        suggestion.save(
            update_fields=["status", "resolved_by", "resolved_at", "admin_notes", "updated_at"]
        )

        return Response(present_threat_suggestion(suggestion))


# ── Shield configuration ───────────────────────────────────────────


class ShieldConfigView(APIView):
    """Get or update the organization's shield configuration."""

    def get(self, request, organization_id):
        organization, membership = get_organization_membership(request, organization_id)
        config, _ = ShieldConfig.objects.get_or_create(organization=organization)
        return Response(present_shield_config(config))

    def patch(self, request, organization_id):
        organization, membership = get_organization_membership(request, organization_id)
        config, _ = ShieldConfig.objects.get_or_create(organization=organization)

        serializer = ShieldConfigUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        update_fields = ["updated_at"]
        for field, value in serializer.validated_data.items():
            setattr(config, field, value)
            update_fields.append(field)

        config.save(update_fields=update_fields)
        return Response(present_shield_config(config))
