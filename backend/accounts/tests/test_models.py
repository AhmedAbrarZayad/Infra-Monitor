from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import Users, PasswordResetOTP, EmailVerificationOTP


class UsersModelTest(TestCase):
    """Unit tests for the Users model."""

    def test_create_user(self):
        """Test creating a user with required fields."""
        user = Users.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            first_name="Test",
            last_name="User",
        )
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.username, "testuser")
        self.assertFalse(user.is_email_verified)
        self.assertEqual(user.role, "viewer")
        self.assertTrue(user.check_password("TestPass123!"))

    def test_email_uniqueness(self):
        """Test that duplicate emails are rejected."""
        Users.objects.create_user(
            username="user1",
            email="duplicate@example.com",
            password="TestPass123!",
        )
        with self.assertRaises(Exception):
            Users.objects.create_user(
                username="user2",
                email="duplicate@example.com",
                password="TestPass123!",
            )

    def test_str_representation(self):
        """Test the string representation returns the email."""
        user = Users.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )
        self.assertEqual(str(user), "test@example.com")

    def test_email_verified_default_false(self):
        """Test that is_email_verified defaults to False."""
        user = Users.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )
        self.assertFalse(user.is_email_verified)


class PasswordResetOTPModelTest(TestCase):
    """Unit tests for the PasswordResetOTP model."""

    def setUp(self):
        self.user = Users.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_create_otp(self):
        """Test creating a password reset OTP."""
        otp = PasswordResetOTP.objects.create(
            user=self.user,
            otp="123456",
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        self.assertEqual(otp.otp, "123456")
        self.assertFalse(otp.is_used)
        self.assertTrue(otp.is_valid)

    def test_otp_expired(self):
        """Test that expired OTPs are marked as invalid."""
        otp = PasswordResetOTP.objects.create(
            user=self.user,
            otp="123456",
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.assertTrue(otp.is_expired)
        self.assertFalse(otp.is_valid)

    def test_otp_used(self):
        """Test that used OTPs are marked as invalid."""
        otp = PasswordResetOTP.objects.create(
            user=self.user,
            otp="123456",
            expires_at=timezone.now() + timedelta(minutes=10),
            is_used=True,
        )
        self.assertFalse(otp.is_valid)


class EmailVerificationOTPModelTest(TestCase):
    """Unit tests for the EmailVerificationOTP model."""

    def setUp(self):
        self.user = Users.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_create_otp(self):
        """Test creating an email verification OTP."""
        otp = EmailVerificationOTP.objects.create(
            user=self.user,
            otp="654321",
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        self.assertEqual(otp.otp, "654321")
        self.assertTrue(otp.is_valid)

    def test_otp_expired(self):
        """Test that expired verification OTPs are invalid."""
        otp = EmailVerificationOTP.objects.create(
            user=self.user,
            otp="654321",
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.assertFalse(otp.is_valid)
