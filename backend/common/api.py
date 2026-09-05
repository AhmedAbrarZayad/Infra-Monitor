from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import LimitOffsetPagination

from accounts.models import Organization, OrganizationMembership


def get_organization_membership(request, organization_id, roles=None):
    organization = get_object_or_404(Organization, pk=organization_id)
    membership = get_object_or_404(
        OrganizationMembership,
        organization=organization,
        user=request.user,
        approved=True,
    )
    if roles and membership.role not in roles:
        raise PermissionDenied("You do not have permission to perform this action.")
    return organization, membership


def paginated_response(request, queryset, presenter):
    paginator = LimitOffsetPagination()
    items = paginator.paginate_queryset(queryset, request)
    return paginator.get_paginated_response([presenter(item) for item in items])


def apply_time_range(queryset, request, field):
    start = parse_datetime(request.query_params.get("from", ""))
    end = parse_datetime(request.query_params.get("to", ""))
    if start:
        queryset = queryset.filter(**{f"{field}__gte": start})
    if end:
        queryset = queryset.filter(**{f"{field}__lte": end})
    return queryset
