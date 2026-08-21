import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Users
from accounts.serializers import ForgotPasswordSerializer
from accounts.services.email_service import GmailOAuth2EmailService
from accounts.services.otp_service import OTPService

logger = logging.getLogger(__name__)


class ForgotPasswordView(APIView):
    """
    POST /api/auth/forgot-password/

    Generates a password reset OTP and sends it via email.
    Always returns a success response to prevent email enumeration.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        # Generic success message regardless of whether user exists
        success_message = (
            "If an account exists with this email, "
            "a password reset code has been sent."
        )

        try:
            user = Users.objects.get(email=email)
        except Users.DoesNotExist:
            # Don't reveal that the email doesn't exist
            return Response(
                {"message": success_message},
                status=status.HTTP_200_OK,
            )

        otp = OTPService.generate_password_reset_otp(user)

        email_service = GmailOAuth2EmailService()
        email_service.send_password_reset_otp(user, otp)

        return Response(
            {"message": success_message},
            status=status.HTTP_200_OK,
        )
