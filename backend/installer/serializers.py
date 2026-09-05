from rest_framework import serializers

from accounts.models import EnrollmentToken


class InternalEnrollmentSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=255, trim_whitespace=False)
    hostname = serializers.CharField(max_length=255)
    os = serializers.CharField(max_length=64)
    architecture = serializers.ChoiceField(choices=("amd64", "arm64"))
    docker_available = serializers.BooleanField(default=False)
    server_url = serializers.URLField(required=False)


class InstallerStatusSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=EnrollmentToken.InstallerStage.values)
    failure_code = serializers.RegexField(
        r"^[A-Z0-9_]{1,64}$",
        required=False,
        allow_blank=True,
    )
    message = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        trim_whitespace=True,
    )

    def validate(self, attrs):
        if attrs["stage"] != EnrollmentToken.InstallerStage.FAILED:
            attrs.pop("failure_code", None)
            attrs.pop("message", None)
        return attrs
