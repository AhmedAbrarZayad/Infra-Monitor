from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Organization, OrganizationMembership, Users
from ml_model.models import AnomalyDetection
from servers.models import Servers, Service


class DashboardApiTests(APITestCase):
    def test_empty_overview_preserves_dashboard_contract(self):
        user = Users.objects.create_user(
            username="owner",
            email="dashboard@example.com",
            password="password123",
            is_email_verified=True,
        )
        organization = Organization.objects.create(name="Dashboard", summary="Test")
        OrganizationMembership.objects.create(
            organization=organization,
            user=user,
            role="OWNER",
            approved=True,
        )
        self.client.force_authenticate(user)

        response = self.client.get(f"/api/organizations/{organization.id}/overview/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["server_count"], 0)
        self.assertFalse(response.data["telemetry_available"])
        self.assertEqual(response.data["recent_anomalies"], [])

    def test_overview_returns_only_latest_tenant_anomalies_with_resource_names(self):
        user = Users.objects.create_user(
            username="owner",
            email="anomalies@example.com",
            password="password123",
            is_email_verified=True,
        )
        organization = Organization.objects.create(name="Dashboard", summary="Test")
        other = Organization.objects.create(name="Other", summary="Other")
        OrganizationMembership.objects.create(
            organization=organization,
            user=user,
            role="OWNER",
            approved=True,
        )
        server = Servers.objects.create(
            organization=organization,
            name="Ubuntu Lab",
            host_name="ubuntu-lab",
            environment="test",
        )
        service = Service.objects.create(
            server_id=server,
            service_name="demo-load",
            display_name="Demo Load",
        )
        other_server = Servers.objects.create(
            organization=other,
            name="Hidden",
            host_name="hidden",
            environment="test",
        )
        values = {
            "cpu_r": 1.0,
            "mem_u": 2.0,
            "disk_r": 3.0,
            "disk_w": 4.0,
            "eth1_fi": 5.0,
            "eth1_fo": 6.0,
        }
        now = timezone.now()
        AnomalyDetection.objects.create(
            organization=organization,
            server_id=server,
            service_id=service,
            anomaly_score=-0.2,
            confidence_score=0.2,
            is_anomaly=True,
            feature_values=values,
            model_version="model-1",
            window_started_at=now,
            window_ended_at=now,
        )
        AnomalyDetection.objects.create(
            organization=organization,
            server_id=server,
            service_id=service,
            anomaly_score=0.1,
            confidence_score=0.1,
            is_anomaly=False,
            feature_values=values,
            model_version="model-2",
            window_started_at=now,
            window_ended_at=now,
        )
        AnomalyDetection.objects.create(
            organization=other,
            server_id=other_server,
            anomaly_score=-0.3,
            confidence_score=0.3,
            is_anomaly=True,
            feature_values=values,
            model_version="hidden",
            window_started_at=now,
            window_ended_at=now,
        )
        self.client.force_authenticate(user)

        response = self.client.get(f"/api/organizations/{organization.id}/overview/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["recent_anomalies"]), 1)
        detection = response.data["recent_anomalies"][0]
        self.assertEqual(detection["server_name"], "Ubuntu Lab")
        self.assertEqual(detection["service_name"], "Demo Load")
        self.assertEqual(detection["model_version"], "model-1")
