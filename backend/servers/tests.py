from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import Organization, OrganizationMembership, Users
from servers.models import Servers


class OperationalApiTests(APITestCase):
    def setUp(self):
        self.user = Users.objects.create_user(username="owner", email="owner@example.com", password="password123", is_email_verified=True)
        self.other = Users.objects.create_user(username="other", email="other@example.com", password="password123", is_email_verified=True)
        self.org = Organization.objects.create(name="A", summary="A")
        self.other_org = Organization.objects.create(name="B", summary="B")
        OrganizationMembership.objects.create(organization=self.org, user=self.user, role="OWNER", approved=True)
        OrganizationMembership.objects.create(organization=self.other_org, user=self.other, role="OWNER", approved=True)
        self.client.force_authenticate(self.user)

    def test_empty_server_collection_and_overview(self):
        response = self.client.get(f"/api/organizations/{self.org.id}/servers/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"], [])
        overview = self.client.get(f"/api/organizations/{self.org.id}/overview/")
        self.assertEqual(overview.status_code, 200)
        self.assertEqual(overview.data["server_count"], 0)
        self.assertFalse(overview.data["telemetry_available"])

    def test_cross_organization_server_is_not_found(self):
        server = Servers.objects.create(organization=self.other_org, name="hidden", host_name="hidden", environment="prod")
        response = self.client.get(f"/api/organizations/{self.org.id}/servers/{server.server_id}/")
        self.assertEqual(response.status_code, 404)

    def test_preferences_are_created_and_updated(self):
        self.assertEqual(self.client.get("/api/auth/me/preferences/").status_code, 200)
        response = self.client.patch("/api/auth/me/preferences/", {"timezone": "Asia/Dhaka", "refresh_interval_seconds": 30}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["timezone"], "Asia/Dhaka")

    def test_health_endpoints(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/health/live/").status_code, 200)
        self.assertEqual(self.client.get("/api/health/ready/").status_code, 200)

# Create your tests here.
