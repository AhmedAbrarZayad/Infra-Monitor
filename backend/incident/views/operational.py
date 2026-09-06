from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import present_user
from alert.presenters import present_alert
from common.api import get_organization_membership, paginated_response
from common.assignment_presenters import present_assignment_event
from common.assignments import (
    UNSET,
    assignment_action,
    assignment_conflict,
    user_id_value,
)
from common.authorization import (
    alerts_visible_to,
    anomalies_visible_to,
    approved_engineers,
    can_manage_work,
    can_operate_work,
    incidents_visible_to,
    logs_visible_to,
)
from incident.models import Incident, IncidentUpdate
from incident.presenters import present_incident
from log.presenters import present_log
from ml_model.presenters import present_anomaly


def add_update(
    incident,
    user,
    action,
    old="",
    new="",
    comment="",
    previous_subject=None,
    new_subject=None,
):
    IncidentUpdate.objects.create(
        incident_id=incident,
        user_id=user,
        action=action,
        old_status=old,
        new_status=new,
        comment=comment,
        previous_subject=previous_subject,
        new_subject=new_subject,
    )


class IncidentListView(APIView):
    def get(self, request, organization_id):
        _, membership = get_organization_membership(request, organization_id)
        queryset = incidents_visible_to(membership).select_related(
            "assigned_to", "server_id", "service"
        )
        search = request.query_params.get("q")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(incident_code__icontains=search)
            )
        for parameter in ["severity", "status"]:
            value = request.query_params.get(parameter)
            if value:
                queryset = queryset.filter(**{parameter: value.upper()})
        if request.query_params.get("assigned_to"):
            queryset = queryset.filter(assigned_to_id=request.query_params["assigned_to"])
        return paginated_response(request, queryset, present_incident)


class IncidentDetailView(APIView):
    def get(self, request, organization_id, incident_id):
        _, membership = get_organization_membership(request, organization_id)
        incident = get_object_or_404(incidents_visible_to(membership), pk=incident_id)
        return Response(present_incident(incident))


class IncidentAcknowledgeView(APIView):
    def post(self, request, organization_id, incident_id):
        _, membership = get_organization_membership(request, organization_id)
        with transaction.atomic():
            incident = get_object_or_404(
                incidents_visible_to(membership, Incident.objects.select_for_update()),
                pk=incident_id,
            )
            if not can_operate_work(membership, incident):
                return Response({"detail": "You do not have permission to acknowledge this incident."}, status=403)
            if not incident.acknowledged_at:
                old_status = incident.status
                incident.acknowledged_at = timezone.now()
                incident.status = Incident.Status.ACKNOWLEDGED
                incident.save(update_fields=["acknowledged_at", "status"])
                add_update(incident, request.user, "ACKNOWLEDGED", old_status, incident.status)
        return Response(present_incident(incident))


class IncidentBulkAcknowledgeView(APIView):
    def post(self, request, organization_id):
        _, membership = get_organization_membership(request, organization_id)
        incident_ids = request.data.get("incident_ids")
        if not isinstance(incident_ids, list) or not incident_ids:
            return Response({"incident_ids": ["Provide a non-empty list."]}, status=400)
        acknowledged = []
        with transaction.atomic():
            incidents = incidents_visible_to(
                membership, Incident.objects.select_for_update()
            ).filter(
                incident_id__in=incident_ids
            )
            for incident in incidents:
                if not incident.acknowledged_at:
                    old_status = incident.status
                    incident.acknowledged_at = timezone.now()
                    incident.status = Incident.Status.ACKNOWLEDGED
                    incident.save(update_fields=["acknowledged_at", "status"])
                    add_update(
                        incident,
                        request.user,
                        "ACKNOWLEDGED",
                        old_status,
                        incident.status,
                    )
                acknowledged.append(str(incident.incident_id))
        requested = set(map(str, incident_ids))
        return Response(
            {
                "acknowledged": acknowledged,
                "not_found_count": len(requested - set(acknowledged)),
            }
        )


class IncidentAssignView(APIView):
    def post(self, request, organization_id, incident_id):
        return self._change(request, organization_id, incident_id)

    def patch(self, request, organization_id, incident_id):
        return self._change(request, organization_id, incident_id)

    def _change(self, request, organization_id, incident_id):
        organization, membership = get_organization_membership(request, organization_id)
        target_id = user_id_value(request.data, "user_id")
        expected_id = user_id_value(
            request.data, "expected_user_id", optional=True
        )
        with transaction.atomic():
            incident = get_object_or_404(
                incidents_visible_to(membership, Incident.objects.select_for_update()),
                pk=incident_id,
            )
            if not can_manage_work(membership, incident):
                return Response({"detail": "You do not have permission to assign this incident."}, status=403)
            if expected_id is not UNSET and expected_id != incident.assigned_to_id:
                return assignment_conflict(incident.assigned_to)
            target = None
            if target_id is not None:
                target_membership = get_object_or_404(
                    approved_engineers(organization),
                    user_id=target_id,
                )
                target = target_membership.user
            if target_id == incident.assigned_to_id:
                return Response(present_incident(incident))
            previous = incident.assigned_to
            action = assignment_action(incident.assigned_to_id, target_id)
            incident.assigned_to = target
            incident.save(update_fields=["assigned_to"])
            add_update(
                incident,
                request.user,
                action,
                previous_subject=previous,
                new_subject=target,
            )
        return Response(present_incident(incident))


class IncidentAssignmentHistoryView(APIView):
    def get(self, request, organization_id, incident_id):
        _, membership = get_organization_membership(request, organization_id)
        incident = get_object_or_404(incidents_visible_to(membership), pk=incident_id)
        queryset = incident.incidentupdate_set.filter(
            action__in=["ASSIGNED", "REASSIGNED", "UNASSIGNED"]
        ).select_related("user_id", "previous_subject", "new_subject")
        return paginated_response(
            request,
            queryset,
            lambda item: present_assignment_event(
                item, "INCIDENT", actor=item.user_id
            ),
        )


class IncidentStatusView(APIView):
    transitions = {
        "NEW": {"ACKNOWLEDGED"},
        "ACKNOWLEDGED": {"INVESTIGATING", "RESOLVED"},
        "INVESTIGATING": {"RESOLVED"},
        "RESOLVED": set(),
    }

    def patch(self, request, organization_id, incident_id):
        _, membership = get_organization_membership(request, organization_id)
        target = str(request.data.get("status", "")).upper()
        with transaction.atomic():
            incident = get_object_or_404(
                incidents_visible_to(membership, Incident.objects.select_for_update()),
                pk=incident_id,
            )
            if not can_operate_work(membership, incident):
                return Response(
                    {"detail": "Only the assignee, owner, or admin may change status."},
                    status=403,
                )
            if target not in self.transitions.get(incident.status, set()):
                return Response(
                    {
                        "detail": "Invalid status transition.",
                        "code": "invalid_incident_transition",
                    },
                    status=409,
                )
            old_status = incident.status
            incident.status = target
            if target == "ACKNOWLEDGED" and not incident.acknowledged_at:
                incident.acknowledged_at = timezone.now()
            if target == "RESOLVED":
                incident.resolved_at = timezone.now()
                incident.resolution_notes = request.data.get(
                    "resolution_notes", incident.resolution_notes
                )
            incident.save()
            add_update(
                incident,
                request.user,
                "STATUS_CHANGED",
                old_status,
                target,
                request.data.get("comment", ""),
            )
        return Response(present_incident(incident))


class IncidentUpdatesView(APIView):
    def get(self, request, organization_id, incident_id):
        _, membership = get_organization_membership(request, organization_id)
        incident = get_object_or_404(incidents_visible_to(membership), pk=incident_id)

        def present_update(update):
            return {
                "id": update.update_id,
                "action": update.action,
                "old_status": update.old_status,
                "new_status": update.new_status,
                "comment": update.comment,
                "user": present_user(update.user_id),
                "created_at": update.created_at,
            }

        return paginated_response(
            request,
            incident.incidentupdate_set.select_related("user_id"),
            present_update,
        )


class IncidentFeedbackView(APIView):
    def post(self, request, organization_id, incident_id):
        _, membership = get_organization_membership(request, organization_id)
        incident = get_object_or_404(incidents_visible_to(membership), pk=incident_id)
        if not can_operate_work(membership, incident):
            return Response(
                {"detail": "Only the assignee, owner, or admin may add feedback."},
                status=403,
            )
        comment = str(request.data.get("comment", "")).strip()
        if not comment:
            return Response({"comment": ["This field is required."]}, status=400)
        update = IncidentUpdate.objects.create(
            incident_id=incident,
            user_id=request.user,
            action="FEEDBACK",
            comment=comment,
        )
        return Response(
            {
                "id": update.update_id,
                "comment": update.comment,
                "created_at": update.created_at,
            },
            status=201,
        )


class IncidentAlertsView(APIView):
    def get(self, request, organization_id, incident_id):
        _, membership = get_organization_membership(request, organization_id)
        incident = get_object_or_404(incidents_visible_to(membership), pk=incident_id)
        alerts = alerts_visible_to(membership).filter(incidentalert__incident_id=incident)
        return paginated_response(request, alerts, present_alert)


class IncidentEvidenceView(APIView):
    def get(self, request, organization_id, incident_id):
        _, membership = get_organization_membership(request, organization_id)
        incident = get_object_or_404(incidents_visible_to(membership), pk=incident_id)
        alerts = alerts_visible_to(membership).filter(incidentalert__incident_id=incident)
        logs = (
            logs_visible_to(membership).filter(service_id=incident.service_id)[:100]
            if incident.service_id
            else []
        )
        anomalies = (
            anomalies_visible_to(membership).filter(service_id=incident.service_id)[:100]
            if incident.service_id
            else []
        )
        return Response(
            {
                "incident_id": incident.incident_id,
                "alerts": [present_alert(item) for item in alerts],
                "logs": [present_log(item) for item in logs],
                "anomalies": [present_anomaly(item) for item in anomalies],
            }
        )
