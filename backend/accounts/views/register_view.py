import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import RegisterSerializer, UserSerializer
from accounts.services.email_service import GmailOAuth2EmailService
from accounts.services.otp_service import OTPService

logger = logging.getLogger(__name__)


class RegisterView(APIView):
    """
    POST /api/auth/register/

    Creates a new user, generates an email verification OTP,
    sends the OTP via email, and returns user data.
    The user must verify their email before they can log in.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate email verification OTP
        otp = OTPService.generate_email_verification_otp(user)

        # Send verification OTP email
        email_service = GmailOAuth2EmailService()
        email_sent = email_service.send_email_verification_otp(user, otp)

        if not email_sent:
            logger.warning(
                "Failed to send verification email to %s. OTP was generated but not delivered.",
                user.email,
            )

        response_data = {
            "message": "Registration successful. Please check your email for the verification code.",
            "user": UserSerializer(user).data,
        }

        # In DEBUG mode, include the OTP in the response for testing
        if settings.DEBUG:
            response_data["debug_otp"] = otp
            response_data["email_sent"] = email_sent

        return Response(response_data, status=status.HTTP_201_CREATED)

