from rest_framework import serializers


class VerifyEmailSerializer(serializers.Serializer):
    """Validates the email + OTP combination for email verification."""

    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)

    def validate_email(self, value):
        return value.lower().strip()
