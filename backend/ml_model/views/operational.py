from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from common.api import apply_time_range, get_organization_membership, paginated_response
from common.assignment_presenters import present_assignment_event
from common.assignments import (
    UNSET,
    assignment_action,
    assignment_conflict,
    user_id_value,
)
from common.authorization import (
    anomalies_visible_to,
    approved_engineers,
    can_manage_work,
    can_operate_work,
)
from ml_model.models import AnomalyAssignmentEvent, AnomalyDetection
from ml_model.presenters import present_anomaly


class AnomalyListView(APIView):
    def get(self, request, organization_id):
        _, membership = get_organization_membership(request, organization_id)
        queryset = anomalies_visible_to(membership).select_related(
            "server_id", "service_id", "assigned_to", "assigned_by"
        )
        for parameter in ["server_id", "service_id", "is_anomaly"]:
            value = request.query_params.get(parameter)
            if value is not None:
                if parameter == "is_anomaly":
                    value = value.lower() == "true"
                queryset = queryset.filter(**{parameter: value})
        queryset = apply_time_range(queryset, request, "detected_at")
        return paginated_response(request, queryset, present_anomaly)


class AnomalyDetailView(APIView):
    def get(self, request, organization_id, detection_id):
        _, membership = get_organization_membership(request, organization_id)
        anomaly = get_object_or_404(
            anomalies_visible_to(membership).select_related(
                "server_id", "service_id", "assigned_to", "assigned_by"
            ),
            pk=detection_id,
        )
        return Response(present_anomaly(anomaly))


class AnomalyResolveView(APIView):
    def post(self, request, organization_id, detection_id):
        _, membership = get_organization_membership(request, organization_id)
        anomaly = get_object_or_404(
            anomalies_visible_to(membership),
            pk=detection_id,
        )
        if not can_operate_work(membership, anomaly):
            return Response({"detail": "You do not have permission to resolve this anomaly."}, status=403)
        if anomaly.resolved_at is None:
            anomaly.resolved_at = timezone.now()
            anomaly.resolved_by = request.user
            anomaly.save(update_fields=["resolved_at", "resolved_by"])
        return Response(present_anomaly(anomaly))


class AnomalyAssignView(APIView):
    def post(self, request, organization_id, detection_id):
        return self._change(request, organization_id, detection_id)

    def patch(self, request, organization_id, detection_id):
        return self._change(request, organization_id, detection_id)

    def _change(self, request, organization_id, detection_id):
        organization, membership = get_organization_membership(request, organization_id)
        target_id = user_id_value(request.data, "user_id")
        expected_id = user_id_value(
            request.data, "expected_user_id", optional=True
        )
        with transaction.atomic():
            anomaly = get_object_or_404(
                anomalies_visible_to(
                    membership, AnomalyDetection.objects.select_for_update()
                ),
                pk=detection_id,
            )
            if not can_manage_work(membership, anomaly):
                return Response({"detail": "You do not have permission to assign this anomaly."}, status=403)
            if expected_id is not UNSET and expected_id != anomaly.assigned_to_id:
                return assignment_conflict(anomaly.assigned_to)
            target = None
            if target_id is not None:
                target_membership = get_object_or_404(
                    approved_engineers(organization), user_id=target_id
                )
                target = target_membership.user
            if target_id == anomaly.assigned_to_id:
                return Response(present_anomaly(anomaly))
            previous = anomaly.assigned_to
            action = assignment_action(anomaly.assigned_to_id, target_id)
            anomaly.assigned_to = target
            anomaly.assigned_by = request.user if target else None
            anomaly.assigned_at = timezone.now() if target else None
            anomaly.save(update_fields=["assigned_to", "assigned_by", "assigned_at"])
            AnomalyAssignmentEvent.objects.create(
                anomaly=anomaly,
                action=action,
                actor=request.user,
                previous_subject=previous,
                new_subject=target,
            )
        return Response(present_anomaly(anomaly))


class AnomalyAssignmentHistoryView(APIView):
    def get(self, request, organization_id, detection_id):
        _, membership = get_organization_membership(request, organization_id)
        anomaly = get_object_or_404(anomalies_visible_to(membership), pk=detection_id)
        queryset = anomaly.assignment_events.select_related(
            "actor", "previous_subject", "new_subject"
        )
        return paginated_response(
            request,
            queryset,
            lambda item: present_assignment_event(item, "ANOMALY"),
        )
