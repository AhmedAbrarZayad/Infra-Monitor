from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from common.api import apply_time_range, get_organization_membership, paginated_response
from common.authorization import logs_visible_to
from log.presenters import present_log


class LogListView(APIView):
    def get(self, request, organization_id):
        _, membership = get_organization_membership(request, organization_id)
        queryset = logs_visible_to(membership)
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
        _, membership = get_organization_membership(request, organization_id)
        entry = get_object_or_404(logs_visible_to(membership), pk=log_id)
        return Response(present_log(entry))
