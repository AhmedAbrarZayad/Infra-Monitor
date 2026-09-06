from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Organization, OrganizationMembership, Users
from ml_model.models import AnomalyDetection
from ml_model.services import FEATURE_NAMES
from servers.models import Servers, Service


@override_settings(ML_SERVICE_TOKEN="test-ml-token")
class InternalDetectionTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="A", summary="A")
        self.server = Servers.objects.create(
            organization=self.organization,
            name="API",
            host_name="api-1",
            environment="test",
        )
        self.service = Service.objects.create(
            server_id=self.server,
            service_name="web",
            display_name="Web",
            status=Servers.Status.HEALTHY,
        )
        start = timezone.now() - timedelta(minutes=5)
        self.payload = {
            "organization_id": str(self.organization.pk),
            "server_id": str(self.server.pk),
            "service_id": str(self.service.pk),
            "is_anomaly": True,
            "anomaly_score": -0.2,
            "confidence_score": 0.2,
            "feature_values": {
                feature: float(index) for index, feature in enumerate(FEATURE_NAMES)
            },
            "window_started_at": start.isoformat(),
            "window_ended_at": (start + timedelta(minutes=5)).isoformat(),
            "model_version": "model-1",
        }

    def post(self, payload=None, token="test-ml-token"):
        return self.client.post(
            "/api/internal/ml/detections/",
            payload or self.payload,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

    def test_requires_shared_token_and_valid_resource_relationship(self):
        self.assertEqual(self.post(token="wrong").status_code, 401)
        response = self.client.post("/api/internal/ml/detections/", self.payload, format="json")
        self.assertEqual(response.status_code, 401)

        other = Organization.objects.create(name="B", summary="B")
        payload = {**self.payload, "organization_id": str(other.pk)}
        self.assertEqual(self.post(payload).status_code, 400)

    def test_stores_and_idempotently_updates_detection_without_lifecycle_change(self):
        first = self.post()
        second_payload = {**self.payload, "anomaly_score": -0.3}
        second = self.post(second_payload)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(AnomalyDetection.objects.count(), 1)
        detection = AnomalyDetection.objects.get()
        self.assertEqual(detection.model_version, "model-1")
        self.assertEqual(detection.anomaly_score, -0.3)
        self.service.refresh_from_db()
        self.assertEqual(self.service.status, Servers.Status.HEALTHY)

    def test_rejects_wrong_feature_order_and_non_finite_values(self):
        reversed_values = dict(reversed(self.payload["feature_values"].items()))
        payload = {**self.payload, "feature_values": reversed_values}
        self.assertEqual(self.post(payload).status_code, 400)
        payload = {
            **self.payload,
            "anomaly_score": "NaN",
        }
        self.assertEqual(self.post(payload).status_code, 400)

    def test_public_anomaly_api_uses_membership_and_returns_model_version(self):
        self.assertEqual(self.post().status_code, 201)
        member = Users.objects.create_user(
            username="member",
            email="member@example.com",
            password="pass",
            is_email_verified=True,
        )
        outsider = Users.objects.create_user(
            username="outsider",
            email="outsider@example.com",
            password="pass",
            is_email_verified=True,
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=member,
            role="ENGINEER",
            approved=True,
        )
        AnomalyDetection.objects.update(assigned_to=member)
        url = f"/api/organizations/{self.organization.pk}/anomalies/"

        self.client.force_authenticate(member)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["model_version"], "model-1")

        self.client.force_authenticate(outsider)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_approved_member_can_resolve_anomaly_idempotently(self):
        detection_id = self.post().data["id"]
        member = Users.objects.create_user(
            username="resolver",
            email="resolver@example.com",
            password="pass",
            is_email_verified=True,
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=member,
            role="ENGINEER",
            approved=True,
        )
        AnomalyDetection.objects.filter(pk=detection_id).update(assigned_to=member)
        self.client.force_authenticate(member)
        url = (
            f"/api/organizations/{self.organization.pk}/anomalies/"
            f"{detection_id}/resolve/"
        )

        first = self.client.post(url)
        second = self.client.post(url)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        detection = AnomalyDetection.objects.get(pk=detection_id)
        self.assertIsNotNone(detection.resolved_at)
        self.assertEqual(detection.resolved_by, member)
