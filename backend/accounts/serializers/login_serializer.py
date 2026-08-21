from django.contrib.auth import authenticate
from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    """
    Validates login credentials.

    Uses email + password. Checks that the user's email is verified
    before allowing login.
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"].lower().strip()
        password = attrs["password"]

        user = authenticate(
            request=self.context.get("request"),
            email=email,
            password=password,
        )

        if user is None:
            raise serializers.ValidationError(
                "Invalid email or password."
            )

        if not user.is_active:
            raise serializers.ValidationError(
                "This account has been deactivated."
            )

        if not user.is_email_verified:
            raise serializers.ValidationError(
                {"email_not_verified": True, "detail": "Please verify your email address before logging in."}
            )

        attrs["user"] = user
        return attrs
