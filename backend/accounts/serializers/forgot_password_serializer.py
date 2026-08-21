from rest_framework import serializers


class ForgotPasswordSerializer(serializers.Serializer):
    """
    Validates the email for the forgot-password flow.

    Always returns success regardless of whether the email exists,
    to prevent user enumeration attacks.
    """

    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower().strip()
