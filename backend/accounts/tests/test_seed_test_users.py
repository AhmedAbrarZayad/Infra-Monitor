from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from accounts.models import OrganizationMembership, Users


class SeedTestUsersCommandTests(TestCase):
    def test_creates_only_three_idempotent_verified_users(self):
        output = StringIO()
        call_command("seed_test_users", stdout=output)

        self.assertEqual(Users.objects.count(), 3)
        self.assertEqual(OrganizationMembership.objects.count(), 0)
        expected = {
            "owner@example.com": ("OWNER", "Owner123!"),
            "admin@example.com": ("ADMIN", "Admin123!"),
            "engineer@example.com": ("ENGINEER", "Engineer123!"),
        }
        for email, (role, password) in expected.items():
            user = Users.objects.get(email=email)
            self.assertEqual(user.role, role)
            self.assertTrue(user.is_email_verified)
            self.assertTrue(user.is_active)
            self.assertTrue(user.check_password(password))

        call_command("seed_test_users", stdout=StringIO())
        self.assertEqual(Users.objects.count(), 3)
        self.assertEqual(OrganizationMembership.objects.count(), 0)
        self.assertIn("no organization memberships", output.getvalue().lower())
