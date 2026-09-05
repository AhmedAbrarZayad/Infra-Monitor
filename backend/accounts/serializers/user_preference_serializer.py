from rest_framework import serializers

from accounts.models import UserPreference


class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = [
            "notifications_enabled",
            "refresh_interval_seconds",
            "timezone",
            "theme",
            "default_environment",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]

    def validate_refresh_interval_seconds(self, value):
        if value < 5 or value > 3600:
            raise serializers.ValidationError("Must be between 5 and 3600 seconds.")
        return value


def present_user(user):
    if not user:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }
