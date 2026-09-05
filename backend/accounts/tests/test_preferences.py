from rest_framework.test import APITestCase

from accounts.models import Users


class PreferencesApiTests(APITestCase):
    def test_preferences_are_created_and_updated(self):
        user = Users.objects.create_user(
            username="owner",
            email="preferences@example.com",
            password="password123",
            is_email_verified=True,
        )
        self.client.force_authenticate(user)

        self.assertEqual(self.client.get("/api/auth/me/preferences/").status_code, 200)
        response = self.client.patch(
            "/api/auth/me/preferences/",
            {"timezone": "Asia/Dhaka", "refresh_interval_seconds": 30},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["timezone"], "Asia/Dhaka")
