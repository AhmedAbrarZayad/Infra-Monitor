import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import ResetPasswordSerializer
from accounts.services.otp_service import OTPService

logger = logging.getLogger(__name__)


class ResetPasswordView(APIView):
    """
    POST /api/auth/reset-password/

    Verifies the password reset OTP and updates the user's password.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]
        new_password = serializer.validated_data["new_password"]

        try:
            user = OTPService.verify_password_reset_otp(email, otp)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])

        return Response(
            {"message": "Password reset successfully. You can now log in with your new password."},
            status=status.HTTP_200_OK,
        )
