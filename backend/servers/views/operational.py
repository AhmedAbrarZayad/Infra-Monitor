import uuid

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import OrganizationMembership
from accounts.serializers import OrganizationMembershipSerializer
from common.api import get_organization_membership, paginated_response
from common.assignment_presenters import present_assignment_event
from common.authorization import (
    alerts_visible_to,
    can_manage_service,
    servers_visible_to,
    services_visible_to,
)
from servers import presenters
from servers.models import (
    Service,
    ServiceAdminAssignment,
    ServiceAdminAssignmentEvent,
)
from servers.presenters import metric_value, present_server, present_service
from servers.services import InvalidMetricError


class ServerListView(APIView):
    def get(self, request, organization_id):
        _, membership = get_organization_membership(request, organization_id)
        queryset = servers_visible_to(membership)
        search = request.query_params.get("q")
        state = request.query_params.get("status")
        environment = request.query_params.get("environment")
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(host_name__icontains=search))
        if state:
            queryset = queryset.filter(status=state.upper())
        if environment:
            queryset = queryset.filter(environment__iexact=environment)
        return paginated_response(request, queryset, lambda item: present_server(item, membership))


class ServerDetailView(APIView):
    @staticmethod
    def get_object(membership, server_id):
        return get_object_or_404(servers_visible_to(membership), pk=server_id)

    def get(self, request, organization_id, server_id):
        _, membership = get_organization_membership(request, organization_id)
        return Response(present_server(self.get_object(membership, server_id), membership))

    def patch(self, request, organization_id, server_id):
        _, membership = get_organization_membership(request, organization_id)
        server = self.get_object(membership, server_id)
        if membership.role != "OWNER":
            return Response({"detail": "Only Owners may edit servers."}, status=403)
        allowed = {"name", "environment"}
        unknown = set(request.data) - allowed
        if unknown:
            return Response(
                {key: ["This field cannot be changed here."] for key in unknown},
                status=400,
            )
        changed = list(allowed & set(request.data))
        for key in changed:
            setattr(server, key, request.data[key])
        server.save(update_fields=changed)
        return Response(present_server(server, membership))


class ServerHealthView(APIView):
    def get(self, request, organization_id, server_id):
        organization, membership = get_organization_membership(request, organization_id)
        server = get_object_or_404(servers_visible_to(membership), pk=server_id)
        if membership.role != "OWNER":
            return Response({"detail": "Host-wide health is available to Owners only."}, status=403)
        codes = [
            "cpu_r",
            "load_1",
            "load_5",
            "mem_u",
            "disk_q",
            "disk_r",
            "disk_w",
            "disk_u",
            "eth1_fi",
            "eth1_fo",
            "tcp_timeouts",
        ]
        return Response(
            {
                "server_id": server.server_id,
                "status": server.status,
                "last_seen_at": server.last_seen_at,
                "metrics": {code: metric_value(server, code) for code in codes},
                "active_alerts": alerts_visible_to(membership).filter(
                    server_id=server,
                    state__in=["ACTIVE", "ACKNOWLEDGED"],
                ).count(),
            }
        )


class MetricRangeView(APIView):
    service_scoped = False

    def get(self, request, organization_id, server_id=None, service_id=None):
        _, membership = get_organization_membership(request, organization_id)
        service = None
        if self.service_scoped:
            service = get_object_or_404(
                services_visible_to(membership), pk=service_id
            )
            server = service.server_id
        else:
            server = get_object_or_404(servers_visible_to(membership), pk=server_id)
            if membership.role != "OWNER":
                from rest_framework.exceptions import PermissionDenied

                raise PermissionDenied("Host-wide metrics are available to Owners only.")

        code = request.query_params.get("metric")
        if not code:
            return Response({"metric": ["This query parameter is required."]}, status=400)
        raw_start = request.query_params.get("from", "")
        raw_end = request.query_params.get("to", "")
        start = parse_datetime(raw_start)
        end = parse_datetime(raw_end)
        if raw_start and start is None:
            return Response({"from": ["Use a valid ISO-8601 timestamp."]}, status=400)
        if raw_end and end is None:
            return Response({"to": ["Use a valid ISO-8601 timestamp."]}, status=400)
        try:
            result = presenters.VictoriaMetricsQueryAdapter().range(
                server=server,
                code=code,
                service=service,
                start=start,
                end=end,
                step=request.query_params.get("step"),
            )
        except (InvalidMetricError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(
            {
                "metric": code,
                "unit": result["unit"],
                "available": result["available"],
                "availability": result["availability"],
                "points": [
                    {
                        "timestamp": point["timestamp"],
                        "value": point["value"],
                        "unit": point["unit"],
                        "labels": point["labels"],
                    }
                    for point in result["points"]
                ],
            }
        )


class ServerMetricRangeView(MetricRangeView):
    pass


class ServiceMetricRangeView(MetricRangeView):
    service_scoped = True


class ServiceListView(APIView):
    def get(self, request, organization_id, server_id):
        _, membership = get_organization_membership(request, organization_id)
        server = get_object_or_404(servers_visible_to(membership), pk=server_id)
        queryset = services_visible_to(membership).filter(server_id=server)
        if request.query_params.get("status"):
            queryset = queryset.filter(status=request.query_params["status"].upper())
        return paginated_response(request, queryset, lambda item: present_service(item, membership))


class ServiceDetailView(APIView):
    @staticmethod
    def get_object(membership, service_id):
        return get_object_or_404(services_visible_to(membership), pk=service_id)

    def get(self, request, organization_id, service_id):
        _, membership = get_organization_membership(request, organization_id)
        return Response(present_service(self.get_object(membership, service_id), membership))

    def patch(self, request, organization_id, service_id):
        _, membership = get_organization_membership(request, organization_id)
        service = self.get_object(membership, service_id)
        if not can_manage_service(membership, service):
            return Response({"detail": "You do not have permission to edit this service."}, status=403)
        if set(request.data) - {"display_name"}:
            return Response({"detail": "Only display_name may be changed."}, status=400)
        service.display_name = request.data.get("display_name", service.display_name)
        service.save(update_fields=["display_name"])
        return Response(present_service(service, membership))


class ServiceHealthView(APIView):
    def get(self, request, organization_id, service_id):
        _, membership = get_organization_membership(request, organization_id)
        service = get_object_or_404(services_visible_to(membership), pk=service_id)
        metrics = {
            code: metric_value(service.server_id, code, service)
            for code in ["cpu_r", "mem_u", "disk_u"]
        }
        return Response({**present_service(service, membership), "metrics": metrics})


class ServiceAdminAssignmentView(APIView):
    @staticmethod
    def _service(membership, service_id):
        return get_object_or_404(
            Service,
            server_id__organization=membership.organization,
            pk=service_id,
        )

    @staticmethod
    def _data(service):
        memberships = OrganizationMembership.objects.filter(
            service_admin_assignments__service=service
        ).select_related("organization", "user")
        return {
            "service_id": service.service_id,
            "admins": OrganizationMembershipSerializer(memberships, many=True).data,
        }

    def get(self, request, organization_id, service_id):
        _, membership = get_organization_membership(request, organization_id, {"OWNER"})
        return Response(self._data(self._service(membership, service_id)))

    @transaction.atomic
    def put(self, request, organization_id, service_id):
        organization, membership = get_organization_membership(
            request, organization_id, {"OWNER"}
        )
        service = get_object_or_404(
            Service.objects.select_for_update(),
            server_id__organization=organization,
            pk=service_id,
        )
        membership_ids = request.data.get("membership_ids")
        if not isinstance(membership_ids, list):
            return Response({"membership_ids": ["Provide a list of membership IDs."]}, status=400)
        try:
            unique_ids = {uuid.UUID(str(item)) for item in membership_ids}
        except (TypeError, ValueError, AttributeError):
            return Response(
                {"membership_ids": ["Every item must be a valid membership UUID."]},
                status=400,
            )
        admins = list(
            OrganizationMembership.objects.filter(
                organization=organization,
                id__in=unique_ids,
                approved=True,
                role=OrganizationMembership.RoleEnum.ADMIN,
            )
        )
        if len(admins) != len(unique_ids):
            return Response(
                {"membership_ids": ["Every ID must be an approved Admin in this organization."]},
                status=400,
            )
        existing = {
            item.membership_id: item
            for item in service.admin_assignments.select_related("membership__user")
        }
        desired = {item.pk: item for item in admins}
        removed_ids = existing.keys() - desired.keys()
        added_ids = desired.keys() - existing.keys()
        for membership_id in removed_ids:
            removed = existing[membership_id]
            ServiceAdminAssignmentEvent.objects.create(
                service=service,
                action=ServiceAdminAssignmentEvent.Action.UNASSIGNED,
                actor=request.user,
                previous_subject=removed.membership.user,
            )
        service.admin_assignments.filter(membership_id__in=removed_ids).delete()
        for membership_id in added_ids:
            admin_membership = desired[membership_id]
            ServiceAdminAssignment.objects.create(
                service=service,
                membership=admin_membership,
                assigned_by=request.user,
            )
            ServiceAdminAssignmentEvent.objects.create(
                service=service,
                action=ServiceAdminAssignmentEvent.Action.ASSIGNED,
                actor=request.user,
                new_subject=admin_membership.user,
            )
        return Response(self._data(service))


class ServiceAdminAssignmentHistoryView(APIView):
    def get(self, request, organization_id, service_id):
        _, membership = get_organization_membership(request, organization_id, {"OWNER"})
        service = ServiceAdminAssignmentView._service(membership, service_id)
        queryset = service.admin_assignment_events.select_related(
            "actor", "previous_subject", "new_subject"
        )
        return paginated_response(
            request,
            queryset,
            lambda item: present_assignment_event(item, "SERVICE"),
        )
