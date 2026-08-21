import logging
import random
import string
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from accounts.models import EmailVerificationOTP, PasswordResetOTP

logger = logging.getLogger(__name__)


class OTPService:
    """Generate and verify OTP codes for email verification and password reset."""

    @staticmethod
    def _generate_code(length: int = 6) -> str:
        """Generate a random numeric OTP code."""
        return "".join(random.choices(string.digits, k=length))

    @classmethod
    def generate_email_verification_otp(cls, user) -> str:
        """
        Generate a 6-digit OTP for email verification.

        Invalidates any existing unused OTPs for this user before creating a new one.
        """
        # Invalidate existing OTPs
        EmailVerificationOTP.objects.filter(
            user=user, is_used=False
        ).update(is_used=True)

        otp_code = cls._generate_code()
        expiry = timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

        EmailVerificationOTP.objects.create(
            user=user,
            otp=otp_code,
            expires_at=expiry,
        )

        logger.info("Email verification OTP generated for user %s", user.email)
        return otp_code

    @classmethod
    def verify_email_otp(cls, email: str, otp: str):
        """
        Verify an email verification OTP.

        Returns the user if valid, raises ValueError otherwise.
        """
        try:
            otp_record = EmailVerificationOTP.objects.select_related("user").get(
                user__email=email,
                otp=otp,
                is_used=False,
            )
        except EmailVerificationOTP.DoesNotExist:
            raise ValueError("Invalid OTP code.")

        if otp_record.is_expired:
            raise ValueError("OTP has expired. Please request a new one.")

        # Mark as used and verify the user's email
        otp_record.is_used = True
        otp_record.save(update_fields=["is_used"])

        user = otp_record.user
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])

        logger.info("Email verified for user %s", user.email)
        return user

    @classmethod
    def generate_password_reset_otp(cls, user) -> str:
        """
        Generate a 6-digit OTP for password reset.

        Invalidates any existing unused OTPs for this user before creating a new one.
        """
        # Invalidate existing OTPs
        PasswordResetOTP.objects.filter(
            user=user, is_used=False
        ).update(is_used=True)

        otp_code = cls._generate_code()
        expiry = timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

        PasswordResetOTP.objects.create(
            user=user,
            otp=otp_code,
            expires_at=expiry,
        )

        logger.info("Password reset OTP generated for user %s", user.email)
        return otp_code

    @classmethod
    def verify_password_reset_otp(cls, email: str, otp: str):
        """
        Verify a password reset OTP.

        Returns the user if valid, raises ValueError otherwise.
        """
        try:
            otp_record = PasswordResetOTP.objects.select_related("user").get(
                user__email=email,
                otp=otp,
                is_used=False,
            )
        except PasswordResetOTP.DoesNotExist:
            raise ValueError("Invalid OTP code.")

        if otp_record.is_expired:
            raise ValueError("OTP has expired. Please request a new one.")

        # Mark as used
        otp_record.is_used = True
        otp_record.save(update_fields=["is_used"])

        logger.info("Password reset OTP verified for user %s", otp_record.user.email)
        return otp_record.user
