from rest_framework import serializers

from accounts.models import Users


class UserSerializer(serializers.ModelSerializer):
    """Read-only serializer for user data returned in API responses."""

    class Meta:
        model = Users
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_email_verified",
            "created_at",
        ]
        read_only_fields = fields
