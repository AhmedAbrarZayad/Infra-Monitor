from datetime import timedelta
from unittest.mock import patch

import snappy
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import EnrollmentToken, Organization, Users, VictoriaMetricsTenant
from accounts.services import TokenService
from servers.models import MonitoringConnection, Servers, Service
from servers.services import MonitoringCredentialService

from .remote_write import WriteRequest


@override_settings(
    MONITORING_PUBLIC_BASE_URL="https://monitor.example",
    VICTORIAMETRICS_INSERT_URL="http://vminsert:8480",
)
class InternalMonitoringApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = Users.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="password",
            is_email_verified=True,
        )
        self.organization = Organization.objects.create(name="Acme", summary="Acme")

    def create_enrollment(self, **overrides):
        raw_token, expires_at = TokenService.generate_enrollment_token()
        values = {
            "organization": self.organization,
            "created_by": self.user,
            "token_hash": TokenService.hash_enrollment_token(raw_token),
            "token_prefix": raw_token[:15],
            "server_name": "Production API",
            "environment": "production",
            "expires_at": expires_at,
        }
        values.update(overrides)
        return EnrollmentToken.objects.create(**values), raw_token

    def enroll(self, **payload_overrides):
        enrollment, raw_token = self.create_enrollment()
        payload = {
            "token": raw_token,
            "hostname": "api-01",
            "os": "ubuntu",
            "architecture": "amd64",
            "docker_available": True,
            "server_url": "http://172.28.144.1:7000",
        }
        payload.update(payload_overrides)
        response = self.client.post(
            "/api/internal/monitoring/enroll/",
            payload,
            format="json",
        )
        return enrollment, response

    def test_enrollment_consumes_token_and_returns_one_time_configuration(self):
        enrollment, response = self.enroll()
        self.assertEqual(response.status_code, 201)
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.stage, EnrollmentToken.Stage.INSTALLING)
        self.assertIsNotNone(enrollment.consumed_at)
        self.assertEqual(enrollment.server.organization, self.organization)
        self.assertTrue(response.data["credential"].startswith("srv_"))
        self.assertEqual(
            MonitoringCredentialService.verify(response.data["credential"]).connection.server,
            enrollment.server,
        )
        self.assertIn("prometheus.exporter.unix", response.data["config"])
        self.assertIn("prometheus.exporter.cadvisor", response.data["config"])
        self.assertIn('discovery.docker "applications"', response.data["config"])
        self.assertIn("monitoring_metrics_port", response.data["config"])
        self.assertIn("monitoring_metrics_path", response.data["config"])
        self.assertIn("monitoring_service_name", response.data["config"])
        self.assertEqual(
            response.data["ingestion_url"], "http://172.28.144.1:7000/api/metrics/write"
        )
        self.assertIn(
            'url = "http://172.28.144.1:7000/api/metrics/write"',
            response.data["config"],
        )
        self.assertTrue(
            VictoriaMetricsTenant.objects.filter(organization=self.organization).exists()
        )

    def test_host_only_enrollment_omits_docker_components(self):
        _, response = self.enroll(hostname="host-only", docker_available=False)
        self.assertEqual(response.status_code, 201)
        self.assertIn("prometheus.exporter.unix", response.data["config"])
        self.assertNotIn("prometheus.exporter.cadvisor", response.data["config"])
        self.assertNotIn("discovery.docker", response.data["config"])

    def test_expired_and_replayed_enrollment_tokens_are_rejected(self):
        expired, token = self.create_enrollment(expires_at=timezone.now() - timedelta(seconds=1))
        payload = {"token": token, "hostname": "expired", "os": "ubuntu", "architecture": "amd64"}
        self.assertEqual(
            self.client.post(
                "/api/internal/monitoring/enroll/", payload, format="json"
            ).status_code,
            401,
        )
        expired.refresh_from_db()
        self.assertEqual(expired.stage, EnrollmentToken.Stage.EXPIRED)

        _, fresh_token = self.create_enrollment()
        fresh_payload = {
            "token": fresh_token,
            "hostname": "fresh",
            "os": "ubuntu",
            "architecture": "amd64",
        }
        self.assertEqual(
            self.client.post(
                "/api/internal/monitoring/enroll/", fresh_payload, format="json"
            ).status_code,
            201,
        )
        self.assertEqual(
            self.client.post(
                "/api/internal/monitoring/enroll/", fresh_payload, format="json"
            ).status_code,
            401,
        )

    def test_existing_hostname_is_safely_reenrolled(self):
        server = Servers.objects.create(
            organization=self.organization,
            name="Existing",
            host_name="api-01",
            environment="production",
        )
        enrollment, response = self.enroll()
        self.assertEqual(response.status_code, 201)
        enrollment.refresh_from_db()
        self.assertIsNotNone(enrollment.consumed_at)
        self.assertEqual(response.data["server_id"], server.server_id)
        self.assertEqual(
            Servers.objects.filter(
                organization=self.organization,
                host_name="api-01",
            ).count(),
            1,
        )

    def test_reenrollment_rotates_the_active_write_credential(self):
        _, first = self.enroll()
        old_credential = first.data["credential"]

        _, second = self.enroll()

        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(second.data["server_id"], first.data["server_id"])
        self.assertIsNone(MonitoringCredentialService.verify(old_credential))
        self.assertIsNotNone(MonitoringCredentialService.verify(second.data["credential"]))

    def test_status_callback_requires_matching_credential_and_bounded_stage(self):
        enrollment, response = self.enroll()
        credential = response.data["credential"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {credential}")
        callback = self.client.post(
            f"/api/internal/monitoring/enrollments/{enrollment.id}/status/",
            {"stage": "COLLECTOR_STARTED"},
            format="json",
        )
        self.assertEqual(callback.status_code, 200)
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.installer_stage, "COLLECTOR_STARTED")
        self.assertIsNotNone(enrollment.server.monitoring_connection.last_callback_at)
        invalid = self.client.post(
            f"/api/internal/monitoring/enrollments/{enrollment.id}/status/",
            {"stage": "MADE_UP"},
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)

    @patch("installer.monitoring_views.httpx.post")
    def test_remote_write_overwrites_identity_and_updates_lifecycle(self, post):
        enrollment, response = self.enroll()
        credential = response.data["credential"]
        tenant = VictoriaMetricsTenant.objects.get(organization=self.organization)
        post.return_value.status_code = 204

        write = WriteRequest()
        series = write.timeseries.add()
        for name, value in (
            ("__name__", "up"),
            ("organization_id", "forged-org"),
            ("server_id", "forged-server"),
            ("vm_account_id", "999"),
            ("service_id", "forged-service"),
            ("service_name", "payments-api"),
            ("service_port", "8000"),
        ):
            label = series.labels.add()
            label.name = name
            label.value = value
        sample = series.samples.add()
        sample.value = 1
        sample.timestamp = 1_700_000_000_000

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {credential}")
        result = self.client.post(
            "/api/metrics/write",
            snappy.compress(write.SerializeToString()),
            content_type="application/x-protobuf",
            HTTP_CONTENT_ENCODING="snappy",
            HTTP_X_PROMETHEUS_REMOTE_WRITE_VERSION="0.1.0",
        )
        self.assertEqual(result.status_code, 204)

        upstream_url = post.call_args.args[0]
        self.assertIn(f"/insert/{tenant.account_id}:0/prometheus/api/v1/write", upstream_url)
        forwarded = WriteRequest()
        forwarded.ParseFromString(snappy.decompress(post.call_args.kwargs["content"]))
        labels = {label.name: label.value for label in forwarded.timeseries[0].labels}
        self.assertEqual(labels["organization_id"], str(self.organization.id))
        self.assertEqual(labels["server_id"], str(response.data["server_id"]))
        self.assertNotIn("vm_account_id", labels)
        service = Service.objects.get(
            server_id_id=response.data["server_id"], service_name="payments-api"
        )
        self.assertEqual(labels["service_id"], str(service.service_id))
        self.assertEqual(service.port, 8000)

        enrollment.refresh_from_db()
        connection = MonitoringConnection.objects.get(server=enrollment.server)
        self.assertEqual(enrollment.stage, EnrollmentToken.Stage.CONNECTED)
        self.assertIsNotNone(enrollment.first_metric_at)
        self.assertEqual(connection.status, MonitoringConnection.Status.CONNECTED)
        service.refresh_from_db()
        self.assertEqual(service.status, Servers.Status.HEALTHY)
        self.assertIsNotNone(service.last_reported_at)

        # Re-delivery and container restarts reuse the stable service identity.
        repeated = self.client.post(
            "/api/metrics/write",
            snappy.compress(write.SerializeToString()),
            content_type="application/x-protobuf",
            HTTP_CONTENT_ENCODING="snappy",
            HTTP_X_PROMETHEUS_REMOTE_WRITE_VERSION="0.1.0",
        )
        self.assertEqual(repeated.status_code, 204)
        self.assertEqual(
            Service.objects.filter(
                server_id_id=response.data["server_id"], service_name="payments-api"
            ).count(),
            1,
        )

    def test_remote_write_rejects_missing_auth_and_bad_protocol(self):
        self.assertEqual(
            self.client.post(
                "/api/metrics/write",
                b"",
                content_type="application/x-protobuf",
            ).status_code,
            401,
        )
        _, response = self.enroll()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['credential']}")
        result = self.client.post(
            "/api/metrics/write",
            b"invalid",
            content_type="application/json",
        )
        self.assertEqual(result.status_code, 415)
