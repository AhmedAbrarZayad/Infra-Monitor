from rest_framework import serializers

from accounts.models import Users


class ResendOTPSerializer(serializers.Serializer):
    """Validates the email for resending an OTP."""

    email = serializers.EmailField()

    def validate_email(self, value):
        normalized = value.lower().strip()
        if not Users.objects.filter(email=normalized).exists():
            raise serializers.ValidationError("No account found with this email.")
        return normalized
