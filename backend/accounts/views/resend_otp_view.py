import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Users
from accounts.serializers import ResendOTPSerializer
from accounts.services.email_service import GmailOAuth2EmailService
from accounts.services.otp_service import OTPService

logger = logging.getLogger(__name__)


class ResendOTPView(APIView):
    """
    POST /api/auth/resend-otp/

    Resends the email verification OTP to the user's email address.
    Only works if the user's email is not already verified.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            user = Users.objects.get(email=email)
        except Users.DoesNotExist:
            # Return success anyway to prevent email enumeration
            return Response(
                {"message": "If an account exists with this email, a new verification code has been sent."},
                status=status.HTTP_200_OK,
            )

        if user.is_email_verified:
            return Response(
                {"detail": "Email is already verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp = OTPService.generate_email_verification_otp(user)

        email_service = GmailOAuth2EmailService()
        email_service.send_email_verification_otp(user, otp)

        return Response(
            {"message": "If an account exists with this email, a new verification code has been sent."},
            status=status.HTTP_200_OK,
        )
