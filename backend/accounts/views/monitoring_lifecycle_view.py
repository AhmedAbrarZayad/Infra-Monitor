import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import EnrollmentToken, Organization, OrganizationMembership
from accounts.serializers import EnrollmentTokenSerializer
from servers.models import MonitoringConnection, ServerWriteCredential, Servers
from servers.services import MonitoringCredentialService


def organization_membership(request, organization_id, administrative=False):
    organization = get_object_or_404(Organization, id=organization_id)
    member = get_object_or_404(
        OrganizationMembership,
        organization=organization,
        user=request.user,
        approved=True,
    )
    if administrative and member.role != OrganizationMembership.RoleEnum.OWNER:
        raise PermissionDenied("You do not have permission to manage monitoring.")
    return organization, member


def credential_metadata(connection):
    now = timezone.now()
    credentials = connection.credentials.all()
    return {
        "active_credential_id": credentials.filter(state=ServerWriteCredential.State.ACTIVE).values_list("id", flat=True).first(),
        "active_count": credentials.filter(state=ServerWriteCredential.State.ACTIVE).count(),
        "grace_count": credentials.filter(state=ServerWriteCredential.State.GRACE, valid_until__gt=now).count(),
        "last_rotated_at": credentials.order_by("-created_at").values_list("created_at", flat=True).first(),
    }


def connection_data(connection):
    return {
        "configured": True,
        "connection_method": connection.connection_method,
        "collector": connection.collector or None,
        "collector_version": connection.collector_version or None,
        "status": connection.status,
        "ingestion_health": connection.ingestion_health,
        "last_callback_at": connection.last_callback_at,
        "last_metric_at": connection.last_metric_at,
        "disconnected_at": connection.disconnected_at,
        "credentials": credential_metadata(connection),
    }


class EnrollmentDetailView(APIView):
    def get(self, request, organization_id, enrollment_id):
        organization, _ = organization_membership(request, organization_id, administrative=True)
        enrollment = get_object_or_404(EnrollmentToken, organization=organization, id=enrollment_id)
        if enrollment.stage in {EnrollmentToken.Stage.CREATED, EnrollmentToken.Stage.INSTALLING} and enrollment.expires_at <= timezone.now():
            enrollment.stage = EnrollmentToken.Stage.EXPIRED
            enrollment.save(update_fields=["stage", "updated_at"])
        data = EnrollmentTokenSerializer(enrollment).data
        try:
            connection = enrollment.server.monitoring_connection if enrollment.server_id else None
        except MonitoringConnection.DoesNotExist:
            connection = None
        data["first_metrics_received"] = enrollment.first_metric_at is not None
        data["connection"] = connection_data(connection) if connection else {"configured": False, "status": "UNCONFIGURED"}
        return Response(data)

    @transaction.atomic
    def delete(self, request, organization_id, enrollment_id):
        organization, _ = organization_membership(request, organization_id, administrative=True)
        enrollment = get_object_or_404(
            EnrollmentToken.objects.select_for_update(), organization=organization, id=enrollment_id
        )
        if enrollment.stage == EnrollmentToken.Stage.CANCELLED:
            return Response(status=204)
        if enrollment.stage in {EnrollmentToken.Stage.CONNECTED, EnrollmentToken.Stage.EXPIRED}:
            return Response(
                {"detail": "This enrollment can no longer be cancelled.", "code": "enrollment_not_cancellable"},
                status=409,
            )
        now = timezone.now()
        enrollment.stage = EnrollmentToken.Stage.CANCELLED
        enrollment.cancelled_at = now
        enrollment.token_hash = hashlib.sha256(secrets.token_bytes(32)).hexdigest()
        enrollment.save(update_fields=["stage", "cancelled_at", "token_hash", "updated_at"])
        if enrollment.server_id:
            connection = MonitoringConnection.objects.select_for_update().filter(server=enrollment.server).first()
            if connection:
                MonitoringCredentialService.revoke_all(connection, now)
                connection.status = MonitoringConnection.Status.DISCONNECTED
                connection.ingestion_health = MonitoringConnection.IngestionHealth.STOPPED
                connection.disconnected_at = now
                connection.disconnected_by = request.user
                connection.save(update_fields=["status", "ingestion_health", "disconnected_at", "disconnected_by", "updated_at"])
            enrollment.server.status = Servers.Status.OFFLINE
            enrollment.server.save(update_fields=["status"])
        return Response(status=204)


class ServerMonitoringView(APIView):
    def get_server(self, organization, server_id):
        return get_object_or_404(Servers, organization=organization, server_id=server_id)

    def get(self, request, organization_id, server_id):
        organization, _ = organization_membership(request, organization_id, administrative=True)
        server = self.get_server(organization, server_id)
        try:
            connection = server.monitoring_connection
        except MonitoringConnection.DoesNotExist:
            return Response({"server_id": server.server_id, "configured": False, "status": "UNCONFIGURED", "ingestion_health": "UNKNOWN", "credentials": None})
        return Response({"server_id": server.server_id, **connection_data(connection)})

    @transaction.atomic
    def delete(self, request, organization_id, server_id):
        organization, _ = organization_membership(request, organization_id, administrative=True)
        server = get_object_or_404(Servers.objects.select_for_update(), organization=organization, server_id=server_id)
        connection = MonitoringConnection.objects.select_for_update().filter(server=server).first()
        if connection and connection.status != MonitoringConnection.Status.DISCONNECTED:
            now = timezone.now()
            MonitoringCredentialService.revoke_all(connection, now)
            connection.status = MonitoringConnection.Status.DISCONNECTED
            connection.ingestion_health = MonitoringConnection.IngestionHealth.STOPPED
            connection.disconnected_at = now
            connection.disconnected_by = request.user
            connection.save(update_fields=["status", "ingestion_health", "disconnected_at", "disconnected_by", "updated_at"])
        if server.status != Servers.Status.OFFLINE:
            server.status = Servers.Status.OFFLINE
            server.save(update_fields=["status"])
        return Response(status=204)


class RotateServerCredentialView(APIView):
    @transaction.atomic
    def post(self, request, organization_id, server_id):
        organization, _ = organization_membership(request, organization_id, administrative=True)
        server = get_object_or_404(Servers, organization=organization, server_id=server_id)
        connection = get_object_or_404(MonitoringConnection.objects.select_for_update(), server=server)
        if connection.status == MonitoringConnection.Status.DISCONNECTED:
            return Response({"detail": "Monitoring is disconnected.", "code": "monitoring_disconnected"}, status=409)
        rotation_key = request.headers.get("Idempotency-Key", "").strip()
        if not rotation_key:
            return Response({"idempotency_key": ["Idempotency-Key header is required."]}, status=400)
        if len(rotation_key) > 255:
            return Response({"idempotency_key": ["Must not exceed 255 characters."]}, status=400)
        if connection.credentials.filter(rotation_key=rotation_key).exists():
            return Response({"detail": "This rotation request was already completed.", "code": "credential_rotation_replayed"}, status=409)
        active = list(connection.credentials.select_for_update().filter(state=ServerWriteCredential.State.ACTIVE))
        if not active:
            return Response({"detail": "No active credential exists to rotate.", "code": "active_credential_missing"}, status=409)
        now = timezone.now()
        overlap_until = now + timedelta(minutes=getattr(settings, "MONITORING_CREDENTIAL_OVERLAP_MINUTES", 15))
        for credential in active:
            credential.state = ServerWriteCredential.State.GRACE
            credential.valid_until = overlap_until
            credential.save(update_fields=["state", "valid_until"])
        try:
            with transaction.atomic():
                replacement, raw = MonitoringCredentialService.issue(connection, request.user, rotation_key)
        except IntegrityError:
            return Response({"detail": "This rotation request was already completed.", "code": "credential_rotation_replayed"}, status=409)
        return Response({
            "credential_id": replacement.id,
            "credential": raw,
            "delivered_once": True,
            "previous_credentials_valid_until": overlap_until,
            "created_at": replacement.created_at,
        }, status=201)
