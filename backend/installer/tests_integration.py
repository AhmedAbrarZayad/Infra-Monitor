import os
import time
from unittest import skipUnless

import httpx
import snappy
from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import EnrollmentToken, Organization, Users, VictoriaMetricsTenant
from accounts.services import TokenService

from .remote_write import WriteRequest


@skipUnless(
    os.getenv("RUN_MONITORING_INTEGRATION") == "1",
    "Set RUN_MONITORING_INTEGRATION=1 with the VictoriaMetrics cluster running.",
)
class VictoriaMetricsIntegrationTests(TestCase):
    """Real Django gateway -> vminsert -> vmstorage -> vmselect smoke test."""

    def test_remote_write_is_queryable_only_in_credential_tenant(self):
        client = APIClient()
        user = Users.objects.create_user(
            username="smoke-owner",
            email="smoke@example.com",
            password="password",
            is_email_verified=True,
        )
        organization = Organization.objects.create(name="Smoke", summary="Smoke")
        raw_token, expires_at = TokenService.generate_enrollment_token()
        enrollment = EnrollmentToken.objects.create(
            organization=organization,
            created_by=user,
            token_hash=TokenService.hash_enrollment_token(raw_token),
            token_prefix=raw_token[:15],
            server_name="Smoke server",
            environment="test",
            expires_at=expires_at,
        )
        enrolled = client.post(
            "/api/internal/monitoring/enroll/",
            {
                "token": raw_token,
                "hostname": f"smoke-{enrollment.id}",
                "os": "linux",
                "architecture": "amd64",
                "docker_available": False,
            },
            format="json",
        )
        self.assertEqual(enrolled.status_code, 201)

        write = WriteRequest()
        series = write.timeseries.add()
        for name, value in (
            ("__name__", "infra_monitor_smoke_metric"),
            ("organization_id", "forged"),
            ("server_id", "forged"),
            ("service_name", "smoke-service"),
        ):
            label = series.labels.add()
            label.name = name
            label.value = value
        sample = series.samples.add()
        sample.value = 1
        sample_time = time.time()
        sample.timestamp = int(sample_time * 1000)

        client.credentials(HTTP_AUTHORIZATION=f"Bearer {enrolled.data['credential']}")
        written = client.post(
            "/api/metrics/write",
            snappy.compress(write.SerializeToString()),
            content_type="application/x-protobuf",
            HTTP_CONTENT_ENCODING="snappy",
            HTTP_X_PROMETHEUS_REMOTE_WRITE_VERSION="0.1.0",
        )
        self.assertIn(written.status_code, {200, 204})

        tenant = VictoriaMetricsTenant.objects.get(organization=organization)
        query_url = (
            f"{settings.VICTORIAMETRICS_SELECT_URL.rstrip('/')}"
            f"/select/{tenant.account_id}%3A{tenant.project_id}/prometheus/api/v1/query_range"
        )
        query = (
            'infra_monitor_smoke_metric{'
            f'server_id="{enrolled.data["server_id"]}"'
            "}"
        )
        result = []
        # vmstorage batches fresh rows before they become searchable. Allow a
        # bounded 30-second convergence window without slowing unit tests;
        # this test only runs when explicitly enabled.
        for _ in range(60):
            response = httpx.get(
                query_url,
                params={
                    "query": query,
                    "start": sample_time - 30,
                    "end": sample_time + 30,
                    "step": 1,
                    "nocache": 1,
                    "latency_offset": "1ms",
                },
                timeout=5,
            )
            response.raise_for_status()
            result = response.json().get("data", {}).get("result", [])
            if result:
                break
            time.sleep(0.5)

        self.assertTrue(result)
        labels = result[0]["metric"]
        self.assertEqual(labels["organization_id"], str(organization.id))
        self.assertEqual(labels["server_id"], str(enrolled.data["server_id"]))
        self.assertNotEqual(labels["organization_id"], "forged")
