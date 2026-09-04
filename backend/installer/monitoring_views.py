import httpx
import snappy
from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.utils import timezone
from google.protobuf.message import DecodeError
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import EnrollmentToken, VictoriaMetricsTenant
from accounts.services import TokenService
from servers.models import MonitoringConnection, Servers, Service
from servers.services import MonitoringCredentialService

from .alloy_config import generate_alloy_config
from .authentication import ServerCredentialAuthentication
from .remote_write import WriteRequest, overwrite_identity, service_metadata
from .serializers import InternalEnrollmentSerializer, InstallerStatusSerializer


def _invalid_enrollment():
    # Use one response for unknown, expired, cancelled, and replayed tokens so
    # callers cannot use this endpoint to inspect token state.
    return Response(
        {"detail": "Invalid or expired enrollment token."},
        status=status.HTTP_401_UNAUTHORIZED,
    )


def _public_metrics_url(request):
    base_url = getattr(settings, "MONITORING_PUBLIC_BASE_URL", "").rstrip("/")
    if base_url:
        return f"{base_url}/api/metrics/write"
    return request.build_absolute_uri("/api/metrics/write")


class InternalEnrollmentView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = InternalEnrollmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        token_hash = TokenService.hash_enrollment_token(payload["token"])

        try:
            with transaction.atomic():
                enrollment = (
                    EnrollmentToken.objects.select_for_update()
                    .select_related("organization")
                    .filter(token_hash=token_hash)
                    .first()
                )
                if enrollment is None:
                    return _invalid_enrollment()

                now = timezone.now()
                if (
                    enrollment.consumed_at is not None
                    or enrollment.cancelled_at is not None
                    or enrollment.stage != EnrollmentToken.Stage.CREATED
                    or enrollment.expires_at <= now
                ):
                    if (
                        enrollment.expires_at <= now
                        and enrollment.stage == EnrollmentToken.Stage.CREATED
                    ):
                        enrollment.stage = EnrollmentToken.Stage.EXPIRED
                        enrollment.save(update_fields=["stage", "updated_at"])
                    return _invalid_enrollment()

                if Servers.objects.filter(
                    organization=enrollment.organization,
                    host_name=payload["hostname"],
                ).exists():
                    return Response(
                        {
                            "detail": "A server with this hostname is already registered.",
                            "code": "hostname_already_registered",
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                server = Servers.objects.create(
                    organization=enrollment.organization,
                    name=enrollment.server_name,
                    host_name=payload["hostname"],
                    environment=enrollment.environment,
                    os_type=payload["os"],
                    status=Servers.Status.UNKNOWN,
                    registered_by=enrollment.created_by,
                    agent_config={
                        "architecture": payload["architecture"],
                        "collector": "alloy",
                        "docker_available": payload["docker_available"],
                    },
                )
                connection = MonitoringConnection.objects.create(
                    server=server,
                    collector="alloy",
                    status=MonitoringConnection.Status.PENDING,
                    ingestion_health=MonitoringConnection.IngestionHealth.UNKNOWN,
                )
                VictoriaMetricsTenant.objects.get_or_create(
                    organization=enrollment.organization
                )
                _, raw_credential = MonitoringCredentialService.issue(
                    connection,
                    actor=enrollment.created_by,
                )

                enrollment.server = server
                enrollment.consumed_at = now
                enrollment.stage = EnrollmentToken.Stage.INSTALLING
                enrollment.save(
                    update_fields=["server", "consumed_at", "stage", "updated_at"]
                )

                ingestion_url = _public_metrics_url(request)
                alloy_config = generate_alloy_config(
                    ingestion_url=ingestion_url,
                    organization_id=enrollment.organization_id,
                    server_id=server.server_id,
                    docker_available=payload["docker_available"],
                )
        except IntegrityError:
            # Covers the organization/hostname uniqueness race without exposing
            # database details.
            return Response(
                {
                    "detail": "A server with this hostname is already registered.",
                    "code": "hostname_already_registered",
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "enrollment_id": enrollment.id,
                "server_id": server.server_id,
                "credential": raw_credential,
                "ingestion_url": ingestion_url,
                "config": alloy_config,
            },
            status=status.HTTP_201_CREATED,
        )


class InstallerStatusView(APIView):
    authentication_classes = [ServerCredentialAuthentication]
    permission_classes = [AllowAny]

    def post(self, request, enrollment_id):
        serializer = InstallerStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        with transaction.atomic():
            enrollment = (
                EnrollmentToken.objects.select_for_update()
                .filter(id=enrollment_id, server=request.auth.connection.server)
                .first()
            )
            if enrollment is None:
                return Response({"detail": "Enrollment not found."}, status=404)

            connection = MonitoringConnection.objects.select_for_update().get(
                id=request.auth.connection_id
            )
            if connection.status == MonitoringConnection.Status.DISCONNECTED:
                return Response(
                    {"detail": "Monitoring is disconnected.", "code": "monitoring_disconnected"},
                    status=409,
                )
            if enrollment.stage in {
                EnrollmentToken.Stage.CONNECTED,
                EnrollmentToken.Stage.EXPIRED,
                EnrollmentToken.Stage.CANCELLED,
            }:
                return Response(
                    {"detail": "Enrollment is no longer installable.", "code": "enrollment_terminal"},
                    status=409,
                )

            now = timezone.now()
            installer_stage = payload["stage"]
            enrollment.installer_stage = installer_stage
            enrollment.stage = (
                EnrollmentToken.Stage.FAILED
                if installer_stage == EnrollmentToken.InstallerStage.FAILED
                else EnrollmentToken.Stage.INSTALLING
            )
            enrollment.failure_code = payload.get("failure_code", "")
            enrollment.failure_message = "".join(
                character
                for character in payload.get("message", "")
                if character.isprintable()
            )
            enrollment.save(
                update_fields=[
                    "installer_stage",
                    "stage",
                    "failure_code",
                    "failure_message",
                    "updated_at",
                ]
            )
            connection.last_callback_at = now
            connection.save(update_fields=["last_callback_at", "updated_at"])
            request.auth.last_used_at = now
            request.auth.save(update_fields=["last_used_at"])

        return Response({"stage": installer_stage, "accepted_at": now})


class MetricsWriteView(APIView):
    authentication_classes = [ServerCredentialAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        content_type = request.content_type
        if content_type != "application/x-protobuf":
            return Response(
                {"detail": "Content-Type must be application/x-protobuf."},
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )
        if request.headers.get("Content-Encoding", "").lower() != "snappy":
            return Response(
                {"detail": "Content-Encoding must be snappy."},
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )
        if request.headers.get("X-Prometheus-Remote-Write-Version") != "0.1.0":
            return Response(
                {"detail": "Only Prometheus Remote Write version 0.1.0 is supported."},
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )

        compressed_limit = getattr(settings, "MONITORING_REMOTE_WRITE_MAX_COMPRESSED_BYTES", 10 * 1024 * 1024)
        decompressed_limit = getattr(settings, "MONITORING_REMOTE_WRITE_MAX_DECOMPRESSED_BYTES", 100 * 1024 * 1024)
        content_length = request.headers.get("Content-Length")
        if content_length and content_length.isdigit() and int(content_length) > compressed_limit:
            return Response({"detail": "Remote write payload is too large."}, status=413)

        compressed = request.body
        if len(compressed) > compressed_limit:
            return Response({"detail": "Remote write payload is too large."}, status=413)
        try:
            raw = snappy.decompress(compressed)
        except snappy.UncompressError:
            return Response({"detail": "Invalid Snappy payload."}, status=400)
        if len(raw) > decompressed_limit:
            return Response({"detail": "Remote write payload is too large."}, status=413)

        write_request = WriteRequest()
        try:
            write_request.ParseFromString(raw)
        except DecodeError:
            return Response({"detail": "Invalid remote write protobuf."}, status=400)
        if not write_request.timeseries:
            return Response({"detail": "Remote write payload contains no time series."}, status=400)

        credential = request.auth
        server = credential.connection.server
        tenant = VictoriaMetricsTenant.objects.filter(
            organization=server.organization
        ).first()
        if tenant is None:
            return Response({"detail": "Metrics tenant is not configured."}, status=503)

        discovered_services = service_metadata(write_request)
        service_ids = {}
        with transaction.atomic():
            for service_name, port in discovered_services.items():
                service, created = Service.objects.get_or_create(
                    server_id=server,
                    service_name=service_name,
                    defaults={
                        "display_name": service_name,
                        "port": port,
                        "status": Servers.Status.UNKNOWN,
                    },
                )
                if not created and port is not None and service.port != port:
                    service.port = port
                    service.save(update_fields=["port"])
                service_ids[service_name] = service.service_id

        overwrite_identity(
            write_request,
            organization_id=server.organization_id,
            server_id=server.server_id,
            service_ids=service_ids,
        )
        forwarded = snappy.compress(write_request.SerializeToString())
        base_url = getattr(settings, "VICTORIAMETRICS_INSERT_URL", "http://vminsert:8480").rstrip("/")
        upstream_url = (
            f"{base_url}/insert/{tenant.account_id}:{tenant.project_id}"
            "/prometheus/api/v1/write"
        )
        headers = {
            "Content-Type": "application/x-protobuf",
            "Content-Encoding": "snappy",
            "X-Prometheus-Remote-Write-Version": "0.1.0",
        }
        try:
            upstream = httpx.post(
                upstream_url,
                content=forwarded,
                headers=headers,
                timeout=getattr(settings, "VICTORIAMETRICS_WRITE_TIMEOUT_SECONDS", 10),
            )
        except httpx.HTTPError:
            return Response({"detail": "Metrics storage is unavailable."}, status=503)

        if upstream.status_code >= 500:
            return Response({"detail": "Metrics storage is unavailable."}, status=503)
        if upstream.status_code >= 400:
            return Response({"detail": "Metrics storage rejected the payload."}, status=400)

        now = timezone.now()
        with transaction.atomic():
            credential = type(credential).objects.select_for_update().get(id=credential.id)
            connection = MonitoringConnection.objects.select_for_update().get(
                id=credential.connection_id
            )
            server = Servers.objects.select_for_update().get(server_id=server.server_id)
            if connection.status == MonitoringConnection.Status.DISCONNECTED:
                return Response({"detail": "Monitoring is disconnected."}, status=409)

            credential.last_used_at = now
            credential.save(update_fields=["last_used_at"])
            connection.status = MonitoringConnection.Status.CONNECTED
            connection.ingestion_health = MonitoringConnection.IngestionHealth.HEALTHY
            connection.last_metric_at = now
            connection.save(
                update_fields=["status", "ingestion_health", "last_metric_at", "updated_at"]
            )
            server.status = Servers.Status.HEALTHY
            server.last_seen_at = now
            server.save(update_fields=["status", "last_seen_at"])
            if service_ids:
                Service.objects.filter(
                    server_id=server,
                    service_id__in=service_ids.values(),
                ).update(status=Servers.Status.HEALTHY, last_reported_at=now)
            enrollment = EnrollmentToken.objects.select_for_update().filter(server=server).first()
            if enrollment is not None:
                enrollment.stage = EnrollmentToken.Stage.CONNECTED
                if enrollment.first_metric_at is None:
                    enrollment.first_metric_at = now
                enrollment.save(update_fields=["stage", "first_metric_at", "updated_at"])

        return HttpResponse(status=upstream.status_code)
