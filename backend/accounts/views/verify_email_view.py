import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.serializers import VerifyEmailSerializer, UserSerializer
from accounts.services.email_service import GmailOAuth2EmailService
from accounts.services.otp_service import OTPService

logger = logging.getLogger(__name__)


class VerifyEmailView(APIView):
    """
    POST /api/auth/verify-email/

    Verifies the user's email using the OTP code sent during registration.
    On success, marks the email as verified, sends a welcome email,
    and returns JWT tokens so the user is immediately logged in.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]

        try:
            user = OTPService.verify_email_otp(email, otp)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Send welcome email now that email is verified
        email_service = GmailOAuth2EmailService()
        email_service.send_welcome_email(user)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Email verified successfully. Welcome to Infra Monitor!",
                "user": UserSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_200_OK,
        )
