from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import OrganizationMembership
from accounts.serializers import present_user
from alert.models import Alert
from alert.presenters import present_alert
from common.api import get_organization_membership, paginated_response
from incident.models import Incident, IncidentUpdate
from incident.presenters import present_incident
from log.models import LogEntry
from log.presenters import present_log
from ml_model.models import AnomalyDetection
from ml_model.presenters import present_anomaly


def add_update(incident, user, action, old="", new="", comment=""):
    IncidentUpdate.objects.create(
        incident_id=incident,
        user_id=user,
        action=action,
        old_status=old,
        new_status=new,
        comment=comment,
    )


class IncidentListView(APIView):
    def get(self, request, organization_id):
        organization, _ = get_organization_membership(request, organization_id)
        queryset = Incident.objects.filter(organization=organization).select_related("assigned_to")
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
        organization, _ = get_organization_membership(request, organization_id)
        incident = get_object_or_404(Incident, organization=organization, pk=incident_id)
        return Response(present_incident(incident))


class IncidentAcknowledgeView(APIView):
    def post(self, request, organization_id, incident_id):
        organization, _ = get_organization_membership(request, organization_id)
        with transaction.atomic():
            incident = get_object_or_404(
                Incident.objects.select_for_update(),
                organization=organization,
                pk=incident_id,
            )
            if not incident.acknowledged_at:
                old_status = incident.status
                incident.acknowledged_at = timezone.now()
                incident.status = Incident.Status.ACKNOWLEDGED
                incident.save(update_fields=["acknowledged_at", "status"])
                add_update(incident, request.user, "ACKNOWLEDGED", old_status, incident.status)
        return Response(present_incident(incident))


class IncidentBulkAcknowledgeView(APIView):
    def post(self, request, organization_id):
        organization, _ = get_organization_membership(request, organization_id)
        incident_ids = request.data.get("incident_ids")
        if not isinstance(incident_ids, list) or not incident_ids:
            return Response({"incident_ids": ["Provide a non-empty list."]}, status=400)
        acknowledged = []
        with transaction.atomic():
            incidents = Incident.objects.select_for_update().filter(
                organization=organization, incident_id__in=incident_ids
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
    self_assign = False

    def post(self, request, organization_id, incident_id):
        return self._change(request, organization_id, incident_id)

    def patch(self, request, organization_id, incident_id):
        return self._change(request, organization_id, incident_id)

    def _change(self, request, organization_id, incident_id):
        roles = None if self.self_assign else {"OWNER", "ADMIN"}
        organization, _ = get_organization_membership(request, organization_id, roles)
        target = request.user if self.self_assign else None
        if not self.self_assign and request.data.get("user_id") is not None:
            target_membership = get_object_or_404(
                OrganizationMembership,
                organization=organization,
                user_id=request.data["user_id"],
                approved=True,
            )
            target = target_membership.user
        with transaction.atomic():
            incident = get_object_or_404(
                Incident.objects.select_for_update(),
                organization=organization,
                pk=incident_id,
            )
            incident.assigned_to = target
            incident.save(update_fields=["assigned_to"])
            add_update(
                incident,
                request.user,
                "ASSIGNED",
                comment="" if target is None else str(target.id),
            )
        return Response(present_incident(incident))


class IncidentSelfAssignView(IncidentAssignView):
    self_assign = True


class IncidentStatusView(APIView):
    transitions = {
        "NEW": {"ACKNOWLEDGED"},
        "ACKNOWLEDGED": {"INVESTIGATING", "RESOLVED"},
        "INVESTIGATING": {"RESOLVED"},
        "RESOLVED": set(),
    }

    def patch(self, request, organization_id, incident_id):
        organization, membership = get_organization_membership(request, organization_id)
        target = str(request.data.get("status", "")).upper()
        with transaction.atomic():
            incident = get_object_or_404(
                Incident.objects.select_for_update(),
                organization=organization,
                pk=incident_id,
            )
            if (
                membership.role not in {"OWNER", "ADMIN"}
                and incident.assigned_to_id != request.user.id
            ):
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
        organization, _ = get_organization_membership(request, organization_id)
        incident = get_object_or_404(Incident, organization=organization, pk=incident_id)

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
        organization, membership = get_organization_membership(request, organization_id)
        incident = get_object_or_404(Incident, organization=organization, pk=incident_id)
        if membership.role not in {"OWNER", "ADMIN"} and incident.assigned_to_id != request.user.id:
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
        organization, _ = get_organization_membership(request, organization_id)
        incident = get_object_or_404(Incident, organization=organization, pk=incident_id)
        alerts = Alert.objects.filter(
            incidentalert__incident_id=incident, organization=organization
        )
        return paginated_response(request, alerts, present_alert)


class IncidentEvidenceView(APIView):
    def get(self, request, organization_id, incident_id):
        organization, _ = get_organization_membership(request, organization_id)
        incident = get_object_or_404(Incident, organization=organization, pk=incident_id)
        alerts = Alert.objects.filter(
            incidentalert__incident_id=incident, organization=organization
        )
        logs = (
            LogEntry.objects.filter(organization=organization, server_id=incident.server_id)[:100]
            if incident.server_id
            else []
        )
        anomalies = (
            AnomalyDetection.objects.filter(
                organization=organization, server_id=incident.server_id
            )[:100]
            if incident.server_id
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
