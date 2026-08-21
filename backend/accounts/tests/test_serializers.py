from django.test import TestCase

from accounts.models import Users
from accounts.serializers import (
    RegisterSerializer,
    LoginSerializer,
    VerifyEmailSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
)


class RegisterSerializerTest(TestCase):
    """Unit tests for RegisterSerializer."""

    def test_valid_registration(self):
        """Test successful registration with valid data."""
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
            "first_name": "New",
            "last_name": "User",
        }
        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertEqual(user.email, "new@example.com")
        self.assertFalse(user.is_email_verified)

    def test_password_mismatch(self):
        """Test that mismatched passwords are rejected."""
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "StrongPass123!",
            "password_confirm": "DifferentPass123!",
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password_confirm", serializer.errors)

    def test_duplicate_email(self):
        """Test that duplicate emails are rejected."""
        Users.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="TestPass123!",
        )
        data = {
            "username": "newuser",
            "email": "existing@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_duplicate_username(self):
        """Test that duplicate usernames are rejected."""
        Users.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            password="TestPass123!",
        )
        data = {
            "username": "existinguser",
            "email": "new@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("username", serializer.errors)

    def test_weak_password(self):
        """Test that weak passwords are rejected by Django validators."""
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "123",
            "password_confirm": "123",
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class LoginSerializerTest(TestCase):
    """Unit tests for LoginSerializer."""

    def setUp(self):
        self.user = Users.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            is_email_verified=True,
        )

    def test_valid_login(self):
        """Test successful login with valid credentials."""
        data = {"email": "test@example.com", "password": "TestPass123!"}
        serializer = LoginSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["user"], self.user)

    def test_invalid_password(self):
        """Test login with wrong password."""
        data = {"email": "test@example.com", "password": "WrongPass123!"}
        serializer = LoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_nonexistent_email(self):
        """Test login with non-existent email."""
        data = {"email": "nonexistent@example.com", "password": "TestPass123!"}
        serializer = LoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_unverified_email(self):
        """Test that unverified email users cannot log in."""
        self.user.is_email_verified = False
        self.user.save()
        data = {"email": "test@example.com", "password": "TestPass123!"}
        serializer = LoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class VerifyEmailSerializerTest(TestCase):
    """Unit tests for VerifyEmailSerializer."""

    def test_valid_data(self):
        """Test valid email + OTP data."""
        data = {"email": "test@example.com", "otp": "123456"}
        serializer = VerifyEmailSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_short_otp(self):
        """Test that OTP shorter than 6 digits is rejected."""
        data = {"email": "test@example.com", "otp": "123"}
        serializer = VerifyEmailSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class ForgotPasswordSerializerTest(TestCase):
    """Unit tests for ForgotPasswordSerializer."""

    def test_valid_email(self):
        """Test valid email."""
        data = {"email": "test@example.com"}
        serializer = ForgotPasswordSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_invalid_email(self):
        """Test invalid email format."""
        data = {"email": "not-an-email"}
        serializer = ForgotPasswordSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class ResetPasswordSerializerTest(TestCase):
    """Unit tests for ResetPasswordSerializer."""

    def test_valid_reset(self):
        """Test valid password reset data."""
        data = {
            "email": "test@example.com",
            "otp": "123456",
            "new_password": "NewStrongPass123!",
            "new_password_confirm": "NewStrongPass123!",
        }
        serializer = ResetPasswordSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_password_mismatch(self):
        """Test password mismatch in reset."""
        data = {
            "email": "test@example.com",
            "otp": "123456",
            "new_password": "NewStrongPass123!",
            "new_password_confirm": "DifferentPass!",
        }
        serializer = ResetPasswordSerializer(data=data)
        self.assertFalse(serializer.is_valid())
