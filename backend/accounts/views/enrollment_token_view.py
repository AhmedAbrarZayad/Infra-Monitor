import shlex
from urllib.parse import urlsplit

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from ..models import EnrollmentToken, Organization, OrganizationMembership
from ..serializers import EnrollmentTokenCreateSerializer, EnrollmentTokenSerializer
from ..services import TokenService


def _install_command(*, install_url, server_url, token):
    """Build a copy/paste command that also survives WSL NAT address changes."""
    install_url = install_url.rstrip("/")
    server_url = server_url.rstrip("/")
    server = urlsplit(server_url)
    installer = urlsplit(install_url)
    port = server.port or (443 if server.scheme == "https" else 80)
    installer_path = installer.path or "/api/monitoring/install.sh"
    if installer.query:
        installer_path = f"{installer_path}?{installer.query}"

    return " ".join(
        (
            f"_im_server={shlex.quote(server_url)};",
            f"_im_installer_url={shlex.quote(install_url)};",
            "if grep -qi microsoft /proc/sys/kernel/osrelease 2>/dev/null; then",
            "_im_gateway=$(ip route show default | awk '/default/ {print $3; exit}');",
            'if [ -z "$_im_gateway" ]; then echo "Unable to detect the Windows WSL gateway." >&2; exit 1; fi;',
            f'_im_server="{server.scheme}://${{_im_gateway}}:{port}";',
            f'_im_installer_url="${{_im_server}}{installer_path}";',
            "fi;",
            "if ! _im_installer=$(mktemp); then exit 1; fi; trap 'rm -f \"$_im_installer\"' EXIT;",
            'curl --connect-timeout 5 --max-time 30 --retry 2 --retry-connrefused -fsSL -o "$_im_installer" "$_im_installer_url" &&',
            f'sudo sh "$_im_installer" --token {shlex.quote(token)} --server "$_im_server"',
        )
    )


class EnrollmentTokenView(GenericAPIView):
    serializer_class = EnrollmentTokenSerializer

    def organization_for_admin(self, request, organization_id):
        organization = get_object_or_404(Organization, id=organization_id)
        membership = get_object_or_404(
            OrganizationMembership, organization=organization, user=request.user, approved=True
        )
        if membership.role not in {
            OrganizationMembership.RoleEnum.OWNER,
            OrganizationMembership.RoleEnum.ADMIN,
        }:
            raise PermissionDenied("You do not have permission to manage monitoring.")
        return organization

    def post(self, request, organization_id):
        organization = self.organization_for_admin(request, organization_id)
        serializer = EnrollmentTokenCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_token, expires_at = TokenService.generate_enrollment_token()
        enrollment = EnrollmentToken.objects.create(
            organization=organization,
            created_by=request.user,
            token_hash=TokenService.hash_enrollment_token(raw_token),
            token_prefix=raw_token[:15],
            expires_at=expires_at,
            **serializer.validated_data,
        )
        data = EnrollmentTokenSerializer(enrollment).data
        install_url = getattr(settings, "MONITORING_INSTALL_URL", "https://monitor.example/install")
        # The installer needs the public backend origin so it can call the
        # internal enrollment and status endpoints. An explicit setting is
        # useful behind a reverse proxy; otherwise derive it from this request.
        server_url = getattr(settings, "MONITORING_PUBLIC_BASE_URL", "").rstrip("/")
        if not server_url:
            server_url = getattr(settings, "MONITORING_SERVER_URL", "").rstrip("/")
        if not server_url:
            server_url = request.build_absolute_uri("/").rstrip("/")

        install_command = _install_command(
            install_url=install_url,
            server_url=server_url,
            token=raw_token,
        )
        data.update({"token": raw_token, "install_command": install_command})
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
