from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from rest_framework.response import Response
from rest_framework.views import APIView

from alert.models import Alert
from common.api import get_organization_membership, paginated_response
from servers import presenters
from servers.models import Servers, Service
from servers.presenters import metric_value, present_server, present_service
from servers.services import InvalidMetricError


class ServerListView(APIView):
    def get(self, request, organization_id):
        organization, _ = get_organization_membership(request, organization_id)
        queryset = Servers.objects.filter(organization=organization)
        search = request.query_params.get("q")
        state = request.query_params.get("status")
        environment = request.query_params.get("environment")
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(host_name__icontains=search))
        if state:
            queryset = queryset.filter(status=state.upper())
        if environment:
            queryset = queryset.filter(environment__iexact=environment)
        return paginated_response(request, queryset, present_server)


class ServerDetailView(APIView):
    @staticmethod
    def get_object(organization, server_id):
        return get_object_or_404(Servers, organization=organization, pk=server_id)

    def get(self, request, organization_id, server_id):
        organization, _ = get_organization_membership(request, organization_id)
        return Response(present_server(self.get_object(organization, server_id)))

    def patch(self, request, organization_id, server_id):
        organization, _ = get_organization_membership(request, organization_id, {"OWNER", "ADMIN"})
        server = self.get_object(organization, server_id)
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
        return Response(present_server(server))


class ServerHealthView(APIView):
    def get(self, request, organization_id, server_id):
        organization, _ = get_organization_membership(request, organization_id)
        server = get_object_or_404(Servers, organization=organization, pk=server_id)
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
                "active_alerts": Alert.objects.filter(
                    organization=organization,
                    server_id=server,
                    state__in=["ACTIVE", "ACKNOWLEDGED"],
                ).count(),
            }
        )


class MetricRangeView(APIView):
    service_scoped = False

    def get(self, request, organization_id, server_id=None, service_id=None):
        organization, _ = get_organization_membership(request, organization_id)
        service = None
        if self.service_scoped:
            service = get_object_or_404(
                Service, server_id__organization=organization, pk=service_id
            )
            server = service.server_id
        else:
            server = get_object_or_404(Servers, organization=organization, pk=server_id)

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
        organization, _ = get_organization_membership(request, organization_id)
        server = get_object_or_404(Servers, organization=organization, pk=server_id)
        queryset = Service.objects.filter(server_id=server)
        if request.query_params.get("status"):
            queryset = queryset.filter(status=request.query_params["status"].upper())
        return paginated_response(request, queryset, present_service)


class ServiceDetailView(APIView):
    @staticmethod
    def get_object(organization, service_id):
        return get_object_or_404(Service, server_id__organization=organization, pk=service_id)

    def get(self, request, organization_id, service_id):
        organization, _ = get_organization_membership(request, organization_id)
        return Response(present_service(self.get_object(organization, service_id)))

    def patch(self, request, organization_id, service_id):
        organization, _ = get_organization_membership(request, organization_id, {"OWNER", "ADMIN"})
        service = self.get_object(organization, service_id)
        if set(request.data) - {"display_name"}:
            return Response({"detail": "Only display_name may be changed."}, status=400)
        service.display_name = request.data.get("display_name", service.display_name)
        service.save(update_fields=["display_name"])
        return Response(present_service(service))


class ServiceHealthView(APIView):
    def get(self, request, organization_id, service_id):
        organization, _ = get_organization_membership(request, organization_id)
        service = get_object_or_404(Service, server_id__organization=organization, pk=service_id)
        metrics = {
            code: metric_value(service.server_id, code, service)
            for code in ["cpu_r", "mem_u", "disk_u"]
        }
        return Response({**present_service(service), "metrics": metrics})
