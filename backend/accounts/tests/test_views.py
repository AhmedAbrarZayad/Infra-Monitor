from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import Users
from accounts.services.otp_service import OTPService


class RegisterViewTest(TestCase):
    """Integration tests for POST /api/auth/register/"""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/register/"

    @patch("accounts.views.register_view.GmailOAuth2EmailService")
    def test_register_success(self, mock_email_service):
        """Test successful registration."""
        mock_email_service.return_value.send_email_verification_otp.return_value = True

        response = self.client.post(
            self.url,
            {
                "username": "newuser",
                "email": "new@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "first_name": "New",
                "last_name": "User",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email"], "new@example.com")
        self.assertFalse(response.data["user"]["is_email_verified"])
        # Verify no tokens are returned (must verify email first)
        self.assertNotIn("tokens", response.data)

    def test_register_missing_fields(self):
        """Test registration with missing required fields."""
        response = self.client.post(
            self.url,
            {"username": "newuser"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.views.register_view.GmailOAuth2EmailService")
    def test_register_duplicate_email(self, mock_email_service):
        """Test registration with already used email."""
        Users.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="TestPass123!",
        )
        response = self.client.post(
            self.url,
            {
                "username": "newuser",
                "email": "existing@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class VerifyEmailViewTest(TestCase):
    """Integration tests for POST /api/auth/verify-email/"""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/verify-email/"
        self.user = Users.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            is_email_verified=False,
        )

    @patch("accounts.views.verify_email_view.GmailOAuth2EmailService")
    def test_verify_email_success(self, mock_email_service):
        """Test successful email verification returns tokens."""
        mock_email_service.return_value.send_welcome_email.return_value = True

        otp = OTPService.generate_email_verification_otp(self.user)
        response = self.client.post(
            self.url,
            {"email": "test@example.com", "otp": otp},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tokens", response.data)
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])

        # User should now be verified
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)

    def test_verify_email_wrong_otp(self):
        """Test verification with incorrect OTP."""
        OTPService.generate_email_verification_otp(self.user)
        response = self.client.post(
            self.url,
            {"email": "test@example.com", "otp": "000000"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginViewTest(TestCase):
    """Integration tests for POST /api/auth/login/"""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/login/"
        self.user = Users.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            is_email_verified=True,
        )

    def test_login_success(self):
        """Test successful login returns tokens."""
        response = self.client.post(
            self.url,
            {"email": "test@example.com", "password": "TestPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tokens", response.data)
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])
        self.assertIn("user", response.data)

    def test_login_wrong_password(self):
        """Test login with incorrect password."""
        response = self.client.post(
            self.url,
            {"email": "test@example.com", "password": "WrongPassword!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_nonexistent_user(self):
        """Test login with non-existent email."""
        response = self.client.post(
            self.url,
            {"email": "ghost@example.com", "password": "TestPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_unverified_email(self):
        """Test that unverified users cannot log in."""
        self.user.is_email_verified = False
        self.user.save()
        response = self.client.post(
            self.url,
            {"email": "test@example.com", "password": "TestPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LogoutViewTest(TestCase):
    """Integration tests for POST /api/auth/logout/"""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/logout/"
        self.user = Users.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            is_email_verified=True,
        )

    def test_logout_success(self):
        """Test successful logout blacklists the refresh token."""
        # Login first to get tokens
        login_response = self.client.post(
            "/api/auth/login/",
            {"email": "test@example.com", "password": "TestPass123!"},
            format="json",
        )
        tokens = login_response.data["tokens"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        response = self.client.post(
            self.url,
            {"refresh": tokens["refresh"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Trying to refresh with blacklisted token should fail
        refresh_response = self.client.post(
            "/api/auth/token/refresh/",
            {"refresh": tokens["refresh"]},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_unauthenticated(self):
        """Test that unauthenticated users cannot logout."""
        response = self.client.post(
            self.url,
            {"refresh": "fake-token"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_missing_refresh_token(self):
        """Test logout without providing refresh token."""
        login_response = self.client.post(
            "/api/auth/login/",
            {"email": "test@example.com", "password": "TestPass123!"},
            format="json",
        )
        tokens = login_response.data["tokens"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MeViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = Users.objects.create_user(
            username="profile-user",
            email="profile@example.com",
            password="TestPass123!",
            first_name="Profile",
            last_name="User",
            is_email_verified=True,
        )

    def test_me_requires_authentication(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_authenticated_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.user.id)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertNotIn("password", response.data)


class ForgotPasswordViewTest(TestCase):
    """Integration tests for POST /api/auth/forgot-password/"""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/forgot-password/"
        self.user = Users.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            is_email_verified=True,
        )

    @patch("accounts.views.forgot_password_view.GmailOAuth2EmailService")
    def test_forgot_password_existing_email(self, mock_email_service):
        """Test forgot password with existing email sends OTP."""
        mock_email_service.return_value.send_password_reset_otp.return_value = True

        response = self.client.post(
            self.url,
            {"email": "test@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)

    def test_forgot_password_nonexistent_email(self):
        """Test forgot password with non-existent email still returns 200 (anti-enumeration)."""
        response = self.client.post(
            self.url,
            {"email": "nonexistent@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ResetPasswordViewTest(TestCase):
    """Integration tests for POST /api/auth/reset-password/"""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/reset-password/"
        self.user = Users.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            is_email_verified=True,
        )

    def test_reset_password_success(self):
        """Test successful password reset with valid OTP."""
        otp = OTPService.generate_password_reset_otp(self.user)
        response = self.client.post(
            self.url,
            {
                "email": "test@example.com",
                "otp": otp,
                "new_password": "NewStrongPass456!",
                "new_password_confirm": "NewStrongPass456!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify user can login with new password
        login_response = self.client.post(
            "/api/auth/login/",
            {"email": "test@example.com", "password": "NewStrongPass456!"},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

    def test_reset_password_wrong_otp(self):
        """Test reset with incorrect OTP."""
        OTPService.generate_password_reset_otp(self.user)
        response = self.client.post(
            self.url,
            {
                "email": "test@example.com",
                "otp": "000000",
                "new_password": "NewStrongPass456!",
                "new_password_confirm": "NewStrongPass456!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_mismatch(self):
        """Test reset with mismatched passwords."""
        otp = OTPService.generate_password_reset_otp(self.user)
        response = self.client.post(
            self.url,
            {
                "email": "test@example.com",
                "otp": otp,
                "new_password": "NewStrongPass456!",
                "new_password_confirm": "DifferentPass!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
