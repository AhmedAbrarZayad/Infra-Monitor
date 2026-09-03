from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from ..models import EnrollmentToken, Organization, OrganizationMembership
from ..serializers import EnrollmentTokenCreateSerializer, EnrollmentTokenSerializer
from ..services import TokenService


class EnrollmentTokenView(GenericAPIView):
    serializer_class = EnrollmentTokenSerializer

    def organization_for_admin(self, request, organization_id):
        organization = get_object_or_404(Organization, id=organization_id)
        membership = get_object_or_404(OrganizationMembership, organization=organization, user=request.user, approved=True)
        if membership.role not in {OrganizationMembership.RoleEnum.OWNER, OrganizationMembership.RoleEnum.ADMIN}:
            raise PermissionDenied("You do not have permission to manage monitoring.")
        return organization

    def post(self, request, organization_id):
        organization = self.organization_for_admin(request, organization_id)
        serializer = EnrollmentTokenCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_token, expires_at = TokenService.generate_enrollment_token()
        enrollment = EnrollmentToken.objects.create(
            organization=organization, created_by=request.user,
            token_hash=TokenService.hash_enrollment_token(raw_token), token_prefix=raw_token[:15],
            expires_at=expires_at, **serializer.validated_data,
        )
        data = EnrollmentTokenSerializer(enrollment).data
        install_url = getattr(settings, "MONITORING_INSTALL_URL", "https://monitor.example/install")
        data.update({"token": raw_token, "install_command": f"curl -fsSL {install_url} | sudo sh -s -- --token {raw_token}"})
        return Response(data, status=status.HTTP_201_CREATED)

    def get(self, request, organization_id):
        organization = self.organization_for_admin(request, organization_id)
        queryset = EnrollmentToken.objects.filter(organization=organization)
        stage = request.query_params.get("stage", "").strip().upper()
        if stage:
            if stage not in {value for value, _ in EnrollmentToken.Stage.choices}:
                return Response({"stage": ["Invalid enrollment stage."]}, status=400)
            queryset = queryset.filter(stage=stage)
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(EnrollmentTokenSerializer(page, many=True).data)
        return Response(EnrollmentTokenSerializer(queryset, many=True).data)
