from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from accounts.models import Users


class RegisterSerializer(serializers.Serializer):
    """
    Validates registration data and creates a new user.

    Does NOT log the user in — email must be verified first.
    """

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False, default="")
    last_name = serializers.CharField(max_length=150, required=False, default="")

    def validate_email(self, value):
        normalized = value.lower().strip()
        if Users.objects.filter(email=normalized).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return normalized

    def validate_username(self, value):
        if Users.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "A user with this username already exists."
            )
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        # Run Django's built-in password validators
        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        user = Users(**validated_data)
        user.set_password(password)
        user.is_email_verified = False
        user.save()
        return user
