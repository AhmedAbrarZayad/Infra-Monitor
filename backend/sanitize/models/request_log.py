import uuid

from django.db import models


class RequestLog(models.Model):
    """A single HTTP request observed on a monitored server or the platform itself.

    Each row represents one access-log line ingested from a Grafana Alloy agent
    (external server) or captured by the platform self-monitoring middleware.
    The ML classifier or Gemini assigns a threat zone after ingestion.
    """

    class Zone(models.TextChoices):
        GREEN = "GREEN", "Safe"
        GRAY = "GRAY", "Suspicious"
        RED = "RED", "Malicious"
        UNCLASSIFIED = "UNCLASSIFIED", "Pending classification"

    class Source(models.TextChoices):
        EXTERNAL = "EXTERNAL", "Monitored server (Alloy agent)"
        PLATFORM = "PLATFORM", "Infra-Monitor API itself"

    class Classifier(models.TextChoices):
        ML_MODEL = "ML_MODEL", "ML model (Random Forest / XGBoost)"
        GEMINI = "GEMINI", "Gemini LLM escalation"
        RULE = "RULE", "Deterministic rule engine"
        UNCLASSIFIED = "UNCLASSIFIED", "Not yet classified"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="request_logs",
    )
    server = models.ForeignKey(
        "servers.Servers",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="request_logs",
        help_text="Null for PLATFORM-source requests.",
    )

    # ── Request metadata ────────────────────────────────────────────
    timestamp = models.DateTimeField(
        db_index=True,
        help_text="When the request was received by the origin server.",
    )
    source_ip = models.GenericIPAddressField(db_index=True)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=2048)
    query_string = models.CharField(max_length=4096, blank=True, default="")
    status_code = models.IntegerField(null=True, blank=True)
    user_agent = models.CharField(max_length=2048, blank=True, default="")
    content_length = models.IntegerField(null=True, blank=True)
    response_time_ms = models.FloatField(null=True, blank=True)
    referer = models.CharField(max_length=2048, blank=True, default="")
    protocol = models.CharField(
        max_length=20, blank=True, default="", help_text='e.g. "HTTP/1.1"'
    )
    headers_digest = models.JSONField(
        default=dict,
        blank=True,
        help_text="Sanitised header summary (no auth tokens or cookies).",
    )

    # ── Source tracking ─────────────────────────────────────────────
    source = models.CharField(
        max_length=10,
        choices=Source.choices,
        default=Source.EXTERNAL,
        db_index=True,
    )

    # ── Classification ──────────────────────────────────────────────
    zone = models.CharField(
        max_length=14,
        choices=Zone.choices,
        default=Zone.UNCLASSIFIED,
        db_index=True,
    )
    confidence = models.FloatField(
        null=True, blank=True, help_text="0.0 – 1.0 classifier confidence."
    )
    threat_signals = models.JSONField(
        default=list,
        blank=True,
        help_text='List of threat signal codes, e.g. ["sql_injection", "path_traversal"].',
    )
    classified_at = models.DateTimeField(null=True, blank=True)
    classified_by = models.CharField(
        max_length=14,
        choices=Classifier.choices,
        default=Classifier.UNCLASSIFIED,
    )

    # ── Feature vector cache ────────────────────────────────────────
    feature_vector = models.JSONField(
        null=True,
        blank=True,
        help_text="Extracted numeric feature vector sent to the ML model.",
    )

    # ── Admin review ────────────────────────────────────────────────
    admin_verdict = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='"confirmed_safe" or "confirmed_threat"',
    )
    reviewed_by = models.ForeignKey(
        "accounts.Users",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_request_logs",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # ── Timestamps ──────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["organization", "zone", "-timestamp"]),
            models.Index(fields=["organization", "source_ip", "-timestamp"]),
            models.Index(fields=["organization", "source", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.method} {self.path} [{self.zone}] from {self.source_ip}"
