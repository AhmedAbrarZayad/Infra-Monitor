import uuid

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Users

from .models import DeviceRegistration


class DeviceRegistrationApiTests(TestCase):
    def setUp(self):
        self.user = Users.objects.create_user(
            username="engineer",
            email="engineer-notifications@example.com",
            password="password123",
            is_email_verified=True,
        )
        self.other = Users.objects.create_user(
            username="other",
            email="other-notifications@example.com",
            password="password123",
            is_email_verified=True,
        )
        self.client = APIClient()
        self.installation_id = uuid.uuid4()
        self.url = f"/api/auth/me/devices/{self.installation_id}/"

    def test_requires_authentication(self):
        self.assertEqual(
            self.client.put(self.url, {"token": "token-a"}, format="json").status_code,
            401,
        )

    def test_registers_and_transfers_installation_to_current_user(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(
            self.client.put(self.url, {"token": "token-a"}, format="json").status_code,
            200,
        )
        self.client.force_authenticate(self.other)
        self.client.put(self.url, {"token": "token-b"}, format="json")

        registration = DeviceRegistration.objects.get(installation_id=self.installation_id)
        self.assertEqual(registration.user, self.other)
        self.assertEqual(registration.token, "token-b")

    def test_user_cannot_deactivate_another_users_installation(self):
        DeviceRegistration.objects.create(
            user=self.user,
            installation_id=self.installation_id,
            token="token-a",
        )
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.delete(self.url).status_code, 204)
        self.assertTrue(DeviceRegistration.objects.get().active)
