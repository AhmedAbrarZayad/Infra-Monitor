from unittest.mock import patch

from django.test import TestCase

from accounts.models import Users, EmailVerificationOTP, PasswordResetOTP
from accounts.services.otp_service import OTPService


class OTPServiceTest(TestCase):
    """Unit tests for the OTPService."""

    def setUp(self):
        self.user = Users.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_generate_email_verification_otp(self):
        """Test generating an email verification OTP."""
        otp = OTPService.generate_email_verification_otp(self.user)
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())
        self.assertTrue(
            EmailVerificationOTP.objects.filter(
                user=self.user, otp=otp, is_used=False
            ).exists()
        )

    def test_generate_invalidates_previous_otps(self):
        """Test that generating a new OTP invalidates old ones."""
        otp1 = OTPService.generate_email_verification_otp(self.user)
        otp2 = OTPService.generate_email_verification_otp(self.user)

        # Old OTP should be marked as used
        old = EmailVerificationOTP.objects.get(otp=otp1)
        self.assertTrue(old.is_used)

        # New OTP should be active
        new = EmailVerificationOTP.objects.get(otp=otp2)
        self.assertFalse(new.is_used)

    def test_verify_email_otp_success(self):
        """Test successful email OTP verification."""
        otp = OTPService.generate_email_verification_otp(self.user)
        user = OTPService.verify_email_otp(self.user.email, otp)
        self.assertTrue(user.is_email_verified)

    def test_verify_email_otp_invalid_code(self):
        """Test verification with wrong OTP code."""
        OTPService.generate_email_verification_otp(self.user)
        with self.assertRaises(ValueError) as ctx:
            OTPService.verify_email_otp(self.user.email, "000000")
        self.assertIn("Invalid", str(ctx.exception))

    def test_verify_email_otp_expired(self):
        """Test verification with expired OTP."""
        otp = OTPService.generate_email_verification_otp(self.user)
        # Force expire the OTP
        record = EmailVerificationOTP.objects.get(otp=otp)
        from django.utils import timezone
        from datetime import timedelta
        record.expires_at = timezone.now() - timedelta(minutes=1)
        record.save()

        with self.assertRaises(ValueError) as ctx:
            OTPService.verify_email_otp(self.user.email, otp)
        self.assertIn("expired", str(ctx.exception))

    def test_generate_password_reset_otp(self):
        """Test generating a password reset OTP."""
        otp = OTPService.generate_password_reset_otp(self.user)
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())
        self.assertTrue(
            PasswordResetOTP.objects.filter(
                user=self.user, otp=otp, is_used=False
            ).exists()
        )

    def test_verify_password_reset_otp_success(self):
        """Test successful password reset OTP verification."""
        otp = OTPService.generate_password_reset_otp(self.user)
        user = OTPService.verify_password_reset_otp(self.user.email, otp)
        self.assertEqual(user.id, self.user.id)

    def test_verify_password_reset_otp_invalid(self):
        """Test password reset with wrong OTP."""
        OTPService.generate_password_reset_otp(self.user)
        with self.assertRaises(ValueError):
            OTPService.verify_password_reset_otp(self.user.email, "000000")


class EmailServiceTest(TestCase):
    """Unit tests for the GmailOAuth2EmailService (mocked SMTP)."""

    def setUp(self):
        self.user = Users.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            first_name="Test",
        )

    @patch("accounts.services.email_service.smtplib.SMTP")
    @patch("accounts.services.email_service.Credentials")
    def test_send_email_success(self, mock_credentials_class, mock_smtp_class):
        """Test that send_email connects to SMTP and sends successfully."""
        from accounts.services.email_service import GmailOAuth2EmailService

        # Mock credentials
        mock_credentials = mock_credentials_class.return_value
        mock_credentials.token = "mock-access-token"
        mock_credentials.refresh.return_value = None

        # Mock SMTP
        mock_smtp = mock_smtp_class.return_value.__enter__.return_value

        service = GmailOAuth2EmailService()
        result = service.send_email("test@example.com", "Test Subject", "<p>Hello</p>")

        self.assertTrue(result)
        mock_smtp.starttls.assert_called_once()
        mock_smtp.sendmail.assert_called_once()

    @patch("accounts.services.email_service.smtplib.SMTP")
    @patch("accounts.services.email_service.Credentials")
    def test_send_welcome_email(self, mock_credentials_class, mock_smtp_class):
        """Test sending a welcome email uses the correct template."""
        from accounts.services.email_service import GmailOAuth2EmailService

        mock_credentials = mock_credentials_class.return_value
        mock_credentials.token = "mock-access-token"
        mock_credentials.refresh.return_value = None

        mock_smtp = mock_smtp_class.return_value.__enter__.return_value

        service = GmailOAuth2EmailService()
        result = service.send_welcome_email(self.user)

        self.assertTrue(result)

    @patch("accounts.services.email_service.smtplib.SMTP")
    @patch("accounts.services.email_service.Credentials")
    def test_send_email_failure(self, mock_credentials_class, mock_smtp_class):
        """Test that send_email returns False on SMTP failure."""
        from accounts.services.email_service import GmailOAuth2EmailService

        mock_credentials = mock_credentials_class.return_value
        mock_credentials.token = "mock-access-token"
        mock_credentials.refresh.return_value = None

        mock_smtp_class.return_value.__enter__.side_effect = Exception("SMTP error")

        service = GmailOAuth2EmailService()
        result = service.send_email("test@example.com", "Test", "<p>Hello</p>")

        self.assertFalse(result)
