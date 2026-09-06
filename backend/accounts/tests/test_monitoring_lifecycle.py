from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import EnrollmentToken, Organization, OrganizationMembership, Users
from accounts.services import TokenService
from servers.models import MonitoringConnection, ServerWriteCredential, Servers
from servers.services import MonitoringCredentialService


@override_settings(MONITORING_CREDENTIAL_OVERLAP_MINUTES=15)
class MonitoringLifecycleApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = Users.objects.create_user(username="owner-life", email="owner-life@example.com", password="pass", is_email_verified=True)
        self.admin = Users.objects.create_user(username="admin-life", email="admin-life@example.com", password="pass", is_email_verified=True)
        self.engineer = Users.objects.create_user(username="engineer-life", email="engineer-life@example.com", password="pass", is_email_verified=True)
        self.other_user = Users.objects.create_user(username="other-life", email="other-life@example.com", password="pass", is_email_verified=True)
        self.org = Organization.objects.create(name="Lifecycle", summary="Lifecycle")
        self.other_org = Organization.objects.create(name="Other lifecycle", summary="Other")
        OrganizationMembership.objects.create(organization=self.org, user=self.owner, role="OWNER", approved=True)
        OrganizationMembership.objects.create(organization=self.org, user=self.admin, role="ADMIN", approved=True)
        OrganizationMembership.objects.create(organization=self.org, user=self.engineer, role="ENGINEER", approved=True)
        OrganizationMembership.objects.create(organization=self.other_org, user=self.other_user, role="OWNER", approved=True)
        self.server = Servers.objects.create(organization=self.org, name="API", host_name="api-1", environment="prod")
        self.connection = MonitoringConnection.objects.create(server=self.server, collector="alloy", collector_version="1.5", status="CONNECTED", ingestion_health="HEALTHY")
        self.credential, self.raw_credential = MonitoringCredentialService.issue(self.connection, self.owner)
        self.client.force_authenticate(self.owner)

    def enrollment(self, **overrides):
        raw, expires = TokenService.generate_enrollment_token()
        values = dict(organization=self.org, created_by=self.owner, token_hash=TokenService.hash_enrollment_token(raw), token_prefix=raw[:15], server_name="API", environment="prod", expires_at=expires)
        values.update(overrides)
        return EnrollmentToken.objects.create(**values)

    def test_enrollment_detail_reports_connection_without_secrets(self):
        enrollment = self.enrollment(server=self.server, stage="CONNECTED", first_metric_at=timezone.now())
        response = self.client.get(f"/api/organizations/{self.org.id}/monitoring/enrollments/{enrollment.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["first_metrics_received"])
        self.assertEqual(response.data["connection"]["collector"], "alloy")
        rendered = str(response.data)
        self.assertNotIn("token_hash", rendered)
        self.assertNotIn("secret_hash", rendered)
        self.assertNotIn(self.raw_credential, rendered)

    def test_expired_enrollment_is_marked_expired(self):
        enrollment = self.enrollment(expires_at=timezone.now() - timedelta(seconds=1))
        response = self.client.get(f"/api/organizations/{self.org.id}/monitoring/enrollments/{enrollment.id}/")
        self.assertEqual(response.data["stage"], "EXPIRED")
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.stage, "EXPIRED")

    def test_cancel_partial_enrollment_revokes_credentials_and_is_idempotent(self):
        enrollment = self.enrollment(server=self.server, stage="INSTALLING", consumed_at=timezone.now())
        url = f"/api/organizations/{self.org.id}/monitoring/enrollments/{enrollment.id}/"
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.delete(url).status_code, 204)
        enrollment.refresh_from_db(); self.credential.refresh_from_db(); self.connection.refresh_from_db(); self.server.refresh_from_db()
        self.assertEqual(enrollment.stage, "CANCELLED")
        self.assertEqual(self.credential.state, "REVOKED")
        self.assertEqual(self.connection.status, "DISCONNECTED")
        self.assertEqual(self.server.status, "OFFLINE")

    def test_connected_and_expired_enrollments_cannot_be_cancelled(self):
        for stage in ("CONNECTED", "EXPIRED"):
            enrollment = self.enrollment(stage=stage)
            response = self.client.delete(f"/api/organizations/{self.org.id}/monitoring/enrollments/{enrollment.id}/")
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.data["code"], "enrollment_not_cancellable")

    def test_monitoring_get_is_owner_only_and_handles_unconfigured_server(self):
        self.client.force_authenticate(self.engineer)
        response = self.client.get(f"/api/organizations/{self.org.id}/servers/{self.server.server_id}/monitoring/")
        self.assertEqual(response.status_code, 403)
        self.client.force_authenticate(self.owner)
        response = self.client.get(f"/api/organizations/{self.org.id}/servers/{self.server.server_id}/monitoring/")
        self.assertTrue(response.data["configured"])
        bare = Servers.objects.create(organization=self.org, name="Bare", host_name="bare", environment="dev")
        response = self.client.get(f"/api/organizations/{self.org.id}/servers/{bare.server_id}/monitoring/")
        self.assertEqual(response.data["status"], "UNCONFIGURED")

    def test_rotation_returns_secret_once_and_preserves_fifteen_minute_overlap(self):
        url = f"/api/organizations/{self.org.id}/servers/{self.server.server_id}/monitoring/credentials/rotate/"
        response = self.client.post(url, HTTP_IDEMPOTENCY_KEY="rotation-1")
        self.assertEqual(response.status_code, 201)
        replacement = ServerWriteCredential.objects.get(id=response.data["credential_id"])
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.state, "GRACE")
        self.assertAlmostEqual((self.credential.valid_until - timezone.now()).total_seconds(), 900, delta=5)
        self.assertNotEqual(replacement.secret_hash, response.data["credential"])
        self.assertEqual(MonitoringCredentialService.verify(response.data["credential"]), replacement)
        replay = self.client.post(url, HTTP_IDEMPOTENCY_KEY="rotation-1")
        self.assertEqual(replay.status_code, 409)
        self.assertEqual(replay.data["code"], "credential_rotation_replayed")
        self.assertNotIn("credential", replay.data)

    def test_rotation_requires_header_role_active_connection_and_credential(self):
        url = f"/api/organizations/{self.org.id}/servers/{self.server.server_id}/monitoring/credentials/rotate/"
        self.assertEqual(self.client.post(url).status_code, 400)
        self.client.force_authenticate(self.engineer)
        self.assertEqual(self.client.post(url, HTTP_IDEMPOTENCY_KEY="engineer").status_code, 403)
        self.client.force_authenticate(self.owner)
        self.connection.status = "DISCONNECTED"; self.connection.save()
        self.assertEqual(self.client.post(url, HTTP_IDEMPOTENCY_KEY="disconnected").status_code, 409)

    def test_disconnect_revokes_all_credentials_and_retains_server(self):
        url = f"/api/organizations/{self.org.id}/servers/{self.server.server_id}/monitoring/"
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertTrue(Servers.objects.filter(pk=self.server.pk).exists())
        self.connection.refresh_from_db(); self.credential.refresh_from_db(); self.server.refresh_from_db()
        self.assertEqual(self.connection.ingestion_health, "STOPPED")
        self.assertEqual(self.credential.state, "REVOKED")
        self.assertEqual(self.server.status, "OFFLINE")

    def test_cross_organization_resources_are_hidden(self):
        self.client.force_authenticate(self.other_user)
        monitoring = self.client.get(f"/api/organizations/{self.other_org.id}/servers/{self.server.server_id}/monitoring/")
        enrollment = self.enrollment()
        detail = self.client.get(f"/api/organizations/{self.other_org.id}/monitoring/enrollments/{enrollment.id}/")
        self.assertEqual(monitoring.status_code, 404)
        self.assertEqual(detail.status_code, 404)
