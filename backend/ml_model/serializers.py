import math

from rest_framework import serializers

from ml_model.services import FEATURE_NAMES


class InternalDetectionSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField()
    server_id = serializers.UUIDField()
    service_id = serializers.UUIDField()
    is_anomaly = serializers.BooleanField()
    anomaly_score = serializers.FloatField()
    confidence_score = serializers.FloatField()
    feature_values = serializers.JSONField()
    window_started_at = serializers.DateTimeField()
    window_ended_at = serializers.DateTimeField()
    model_version = serializers.CharField(max_length=64)

    def validate_anomaly_score(self, value):
        if not math.isfinite(value):
            raise serializers.ValidationError("Score must be finite.")
        return value

    def validate_confidence_score(self, value):
        if not math.isfinite(value):
            raise serializers.ValidationError("Score must be finite.")
        return value

    def validate_feature_values(self, value):
        if not isinstance(value, dict) or tuple(value) != FEATURE_NAMES:
            raise serializers.ValidationError(
                "Feature values must use the ordered container_iforest_v1 schema."
            )
        if any(
            isinstance(item, bool)
            or not isinstance(item, (int, float))
            or not math.isfinite(float(item))
            for item in value.values()
        ):
            raise serializers.ValidationError("Feature values must be finite numbers.")
        return {feature: float(value[feature]) for feature in FEATURE_NAMES}

    def validate(self, attrs):
        if attrs["window_started_at"] >= attrs["window_ended_at"]:
            raise serializers.ValidationError(
                "window_started_at must be earlier than window_ended_at."
            )
        return attrs
