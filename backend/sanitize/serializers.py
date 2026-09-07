"""DRF serializers for sanitize input validation.

These handle write-side validation only. Read-side formatting is done by the
presenters module.
"""

from rest_framework import serializers


class RequestLogIngestionSerializer(serializers.Serializer):
    """Validates a single request-log entry from the Alloy agent or platform
    middleware."""

    timestamp = serializers.DateTimeField()
    source_ip = serializers.IPAddressField()
    method = serializers.CharField(max_length=10)
    path = serializers.CharField(max_length=2048)
    query_string = serializers.CharField(max_length=4096, required=False, default="")
    status_code = serializers.IntegerField(required=False, allow_null=True)
    user_agent = serializers.CharField(max_length=2048, required=False, default="")
    content_length = serializers.IntegerField(required=False, allow_null=True)
    response_time_ms = serializers.FloatField(required=False, allow_null=True)
    referer = serializers.CharField(max_length=2048, required=False, default="")
    protocol = serializers.CharField(max_length=20, required=False, default="")
    headers_digest = serializers.DictField(required=False, default=dict)


class RequestLogBatchSerializer(serializers.Serializer):
    """Wraps a batch of request-log entries for the internal ingestion API."""

    server_id = serializers.UUIDField()
    entries = RequestLogIngestionSerializer(many=True)


class ThreatSuggestionActionSerializer(serializers.Serializer):
    """Validates admin accept/dismiss actions on a threat suggestion."""

    action = serializers.ChoiceField(choices=["accept", "dismiss"])
    notes = serializers.CharField(max_length=2000, required=False, default="")


class AdminVerdictSerializer(serializers.Serializer):
    """Validates admin verdict on a single request log."""

    verdict = serializers.ChoiceField(choices=["confirmed_safe", "confirmed_threat"])


class ShieldConfigUpdateSerializer(serializers.Serializer):
    """Validates partial updates to the shield configuration."""

    enabled = serializers.BooleanField(required=False)
    gemini_escalation = serializers.BooleanField(required=False)
    platform_self_monitor = serializers.BooleanField(required=False)
    red_suggestion_threshold = serializers.IntegerField(min_value=1, max_value=1000, required=False)
    gray_suggestion_threshold = serializers.IntegerField(
        min_value=1, max_value=5000, required=False
    )
    suggestion_window_minutes = serializers.IntegerField(
        min_value=1, max_value=1440, required=False
    )
    notify_on_red = serializers.BooleanField(required=False)
