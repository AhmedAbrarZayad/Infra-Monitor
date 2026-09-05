from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from alert.models import Alert
from alert.presenters import present_alert
from common.api import apply_time_range, get_organization_membership, paginated_response


class AlertListView(APIView):
    def get(self, request, organization_id):
        organization, _ = get_organization_membership(request, organization_id)
        queryset = Alert.objects.filter(organization=organization)
        for key in ["state", "severity", "server_id", "service_id"]:
            value = request.query_params.get(key)
            if value:
                queryset = queryset.filter(
                    **{key: value.upper() if key in {"state", "severity"} else value}
                )
        search = request.query_params.get("q")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        queryset = apply_time_range(queryset, request, "triggered_at")
        return paginated_response(request, queryset, present_alert)


class AlertDetailView(APIView):
    def get(self, request, organization_id, alert_id):
        organization, _ = get_organization_membership(request, organization_id)
        alert = get_object_or_404(Alert, organization=organization, pk=alert_id)
        return Response(present_alert(alert))


class AlertActionView(APIView):
    resolve = False

    def post(self, request, organization_id, alert_id):
        roles = {"OWNER", "ADMIN"} if self.resolve else None
        organization, _ = get_organization_membership(request, organization_id, roles)
        with transaction.atomic():
            alert = get_object_or_404(
                Alert.objects.select_for_update(), organization=organization, pk=alert_id
            )
            if self.resolve:
                if alert.state == Alert.State.RESOLVED:
                    return Response(present_alert(alert))
                alert.state = Alert.State.RESOLVED
                alert.cleared_at = timezone.now()
                alert.cleared_by = request.user
                alert.save(update_fields=["state", "cleared_at", "cleared_by"])
            else:
                if alert.state == Alert.State.RESOLVED:
                    return Response(
                        {
                            "detail": "Resolved alerts cannot be acknowledged.",
                            "code": "alert_resolved",
                        },
                        status=409,
                    )
                if alert.state != Alert.State.ACKNOWLEDGED:
                    alert.state = Alert.State.ACKNOWLEDGED
                    alert.acknowledged_at = timezone.now()
                    alert.acknowledged_by = request.user
                    alert.save(update_fields=["state", "acknowledged_at", "acknowledged_by"])
        return Response(present_alert(alert))


class AlertAcknowledgeView(AlertActionView):
    pass


class AlertResolveView(AlertActionView):
    resolve = True
