from unittest.mock import patch
from uuid import uuid4

from django.urls import resolve
from rest_framework.test import APITestCase


class HealthApiTests(APITestCase):
    @patch("infra_monitor.health_views.connection")
    def test_public_health_endpoints(self, connection):
        connection.cursor.return_value.__enter__.return_value.execute.return_value = None

        self.assertEqual(self.client.get("/api/health/live/").status_code, 200)
        self.assertEqual(self.client.get("/api/health/ready/").status_code, 200)


class RouteCompositionTests(APITestCase):
    def test_all_relocated_operational_routes_resolve(self):
        organization_id = uuid4()
        resource_id = uuid4()
        organization_prefix = f"/api/organizations/{organization_id}"
        paths = [
            f"{organization_prefix}/overview/",
            f"{organization_prefix}/analytics/",
            f"{organization_prefix}/servers/",
            f"{organization_prefix}/servers/{resource_id}/",
            f"{organization_prefix}/servers/{resource_id}/health/",
            f"{organization_prefix}/servers/{resource_id}/metrics/",
            f"{organization_prefix}/servers/{resource_id}/services/",
            f"{organization_prefix}/services/{resource_id}/",
            f"{organization_prefix}/services/{resource_id}/admins/",
            f"{organization_prefix}/services/{resource_id}/health/",
            f"{organization_prefix}/services/{resource_id}/metrics/",
            f"{organization_prefix}/alerts/",
            f"{organization_prefix}/alerts/{resource_id}/",
            f"{organization_prefix}/alerts/{resource_id}/acknowledge/",
            f"{organization_prefix}/alerts/{resource_id}/resolve/",
            f"{organization_prefix}/logs/",
            f"{organization_prefix}/logs/{resource_id}/",
            f"{organization_prefix}/incidents/",
            f"{organization_prefix}/incidents/bulk-acknowledge/",
            f"{organization_prefix}/incidents/{resource_id}/",
            f"{organization_prefix}/incidents/{resource_id}/acknowledge/",
            f"{organization_prefix}/incidents/{resource_id}/assignment/",
            f"{organization_prefix}/incidents/{resource_id}/status/",
            f"{organization_prefix}/incidents/{resource_id}/updates/",
            f"{organization_prefix}/incidents/{resource_id}/feedback/",
            f"{organization_prefix}/incidents/{resource_id}/alerts/",
            f"{organization_prefix}/incidents/{resource_id}/evidence/",
            f"{organization_prefix}/anomalies/",
            f"{organization_prefix}/anomalies/{resource_id}/",
            f"{organization_prefix}/anomalies/{resource_id}/assignment/",
            "/api/auth/me/preferences/",
            "/api/health/live/",
            "/api/health/ready/",
            "/api/internal/health/dependencies/",
            "/api/internal/health/workers/",
            "/api/internal/logs/batches/",
            "/api/metrics/write",
        ]

        for path in paths:
            with self.subTest(path=path):
                self.assertIsNotNone(resolve(path).func)
