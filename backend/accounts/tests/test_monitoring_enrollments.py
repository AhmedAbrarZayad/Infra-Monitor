from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import EnrollmentToken, Organization, OrganizationMembership, Users
from accounts.services import TokenService
from accounts.views.enrollment_token_view import _install_command


class InstallCommandTests(TestCase):
    def test_trailing_slashes_do_not_create_double_slash_paths(self):
        command = _install_command(
            install_url="http://192.168.0.107:7000/api/monitoring/install.sh/",
            server_url="http://192.168.0.107:7000/",
            token="enroll_test",
        )

        self.assertNotIn(":7000//api/", command)
        self.assertIn('_im_server="http://${_im_gateway}:7000"', command)
        self.assertIn('sudo sh "$_im_installer"', command)


@override_settings(MONITORING_INSTALL_URL="https://example.test/install")
class MonitoringEnrollmentApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = Users.objects.create_user(
            username="owner", email="owner@example.com", password="pass", is_email_verified=True
        )
        self.admin = Users.objects.create_user(
            username="admin", email="admin@example.com", password="pass", is_email_verified=True
        )
        self.engineer = Users.objects.create_user(
            username="engineer",
            email="engineer@example.com",
            password="pass",
            is_email_verified=True,
        )
        self.outsider = Users.objects.create_user(
            username="outsider",
            email="outsider@example.com",
            password="pass",
            is_email_verified=True,
        )
        self.organization = Organization.objects.create(name="Acme", summary="Acme")
        self.other = Organization.objects.create(name="Other", summary="Other")
        OrganizationMembership.objects.create(
            organization=self.organization, user=self.owner, role="OWNER", approved=True
        )
        OrganizationMembership.objects.create(
            organization=self.organization, user=self.admin, role="ADMIN", approved=True
        )
        OrganizationMembership.objects.create(
            organization=self.organization, user=self.engineer, role="ENGINEER", approved=True
        )
        self.url = f"/api/organizations/{self.organization.id}/monitoring/enrollments/"

    def test_owner_creates_enrollment_and_raw_token_is_not_stored(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            self.url, {"server_name": "Production API", "environment": "Production"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        enrollment = EnrollmentToken.objects.get(id=response.data["enrollment_id"])
        self.assertTrue(response.data["token"].startswith("enroll_"))
        self.assertNotEqual(enrollment.token_hash, response.data["token"])
        self.assertEqual(
            enrollment.token_hash, TokenService.hash_enrollment_token(response.data["token"])
        )
        self.assertNotIn(
            response.data["token"], str(EnrollmentToken.objects.values().get(id=enrollment.id))
        )
        self.assertIn(response.data["token"], response.data["install_command"])
        self.assertIn("ip route show default", response.data["install_command"])
        self.assertIn("--connect-timeout 5 --max-time 30", response.data["install_command"])
        self.assertIn('--server "$_im_server"', response.data["install_command"])
        self.assertIn("${_im_gateway}", response.data["install_command"])
        self.assertNotIn("||", response.data["install_command"])

    def test_only_owner_can_create_enrollments(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(
            self.client.post(self.url, {"server_name": "A", "environment": "dev"}).status_code, 403
        )
        self.client.force_authenticate(self.engineer)
        self.assertEqual(
            self.client.post(self.url, {"server_name": "B", "environment": "dev"}).status_code, 403
        )

    def test_list_is_organization_scoped_and_never_returns_token_material(self):
        raw, expiry = TokenService.generate_enrollment_token()
        EnrollmentToken.objects.create(
            organization=self.organization,
            created_by=self.owner,
            token_hash=TokenService.hash_enrollment_token(raw),
            token_prefix=raw[:15],
            server_name="Visible",
            environment="prod",
            expires_at=expiry,
        )
        other_raw, other_expiry = TokenService.generate_enrollment_token()
        EnrollmentToken.objects.create(
            organization=self.other,
            created_by=self.outsider,
            token_hash=TokenService.hash_enrollment_token(other_raw),
            token_prefix=other_raw[:15],
            server_name="Hidden",
            environment="prod",
            expires_at=other_expiry,
        )
        self.client.force_authenticate(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["server_name"], "Visible")
        self.assertNotIn("token", response.data["results"][0])
        self.assertNotIn("token_hash", response.data["results"][0])

    def test_outsider_receives_404_and_invalid_stage_is_rejected(self):
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get(self.url, {"stage": "nonsense"}).status_code, 400)

    def test_authentication_and_required_input(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("server_name", response.data)
        self.assertIn("environment", response.data)
