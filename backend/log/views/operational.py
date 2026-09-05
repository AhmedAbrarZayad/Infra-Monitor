from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from common.api import apply_time_range, get_organization_membership, paginated_response
from log.models import LogEntry
from log.presenters import present_log


class LogListView(APIView):
    def get(self, request, organization_id):
        organization, _ = get_organization_membership(request, organization_id)
        queryset = LogEntry.objects.filter(organization=organization)
        search = request.query_params.get("q")
        if search:
            queryset = queryset.filter(Q(message__icontains=search) | Q(source__icontains=search))
        for parameter, field in [
            ("level", "log_level"),
            ("source", "source"),
            ("server_id", "server_id"),
            ("service_id", "service_id"),
        ]:
            value = request.query_params.get(parameter)
            if value:
                queryset = queryset.filter(**{field: value})
        queryset = apply_time_range(queryset, request, "logged_at")
        return paginated_response(request, queryset, present_log)


class LogDetailView(APIView):
    def get(self, request, organization_id, log_id):
        organization, _ = get_organization_membership(request, organization_id)
        entry = get_object_or_404(LogEntry, organization=organization, pk=log_id)
        return Response(present_log(entry))
