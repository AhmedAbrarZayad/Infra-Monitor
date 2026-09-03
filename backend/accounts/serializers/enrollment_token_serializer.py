from rest_framework import serializers

from ..models import EnrollmentToken


class EnrollmentTokenSerializer(serializers.ModelSerializer):
    enrollment_id = serializers.UUIDField(source="id", read_only=True)
    server_id = serializers.UUIDField(read_only=True, allow_null=True)
    is_used = serializers.BooleanField(read_only=True)

    class Meta:
        model = EnrollmentToken
        fields = [
            "enrollment_id", "server_name", "environment", "stage", "expires_at",
            "is_used", "server_id", "first_metric_at", "failure_code",
            "failure_message", "created_at", "updated_at",
        ]
