from rest_framework import serializers


class EnrollmentTokenCreateSerializer(serializers.Serializer):
    server_name = serializers.CharField(max_length=255)
    environment = serializers.CharField(max_length=64)

    def validate_server_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_environment(self, value):
        value = value.strip().lower()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value
