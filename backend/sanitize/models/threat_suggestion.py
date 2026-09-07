import uuid

from django.db import models


class ThreatSuggestion(models.Model):
    """A system-generated suggestion presented to the admin when an IP exceeds
    the configured RED or GRAY threshold.

    The admin can accept (acknowledge the threat), dismiss (mark as safe), or
    ignore the suggestion. Accepting does NOT auto-block the IP — it only
    records the admin's acknowledgement so they can take manual action through
    their own firewall / reverse-proxy. This is a suggestion-only, non-blocking
    system by design.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Awaiting admin review"
        ACCEPTED = "ACCEPTED", "Admin acknowledged as threat"
        DISMISSED = "DISMISSED", "Admin dismissed as safe"

    class TriggerZone(models.TextChoices):
        RED = "RED", "Triggered by RED-zone threshold"
        GRAY = "GRAY", "Triggered by GRAY-zone threshold"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="threat_suggestions",
    )
    ip_address = models.GenericIPAddressField(db_index=True)

    # ── Trigger context ─────────────────────────────────────────────
    trigger_zone = models.CharField(
        max_length=4,
        choices=TriggerZone.choices,
    )
    request_count = models.IntegerField(
        help_text="Number of zone-matching requests from this IP in the window.",
    )
    window_start = models.DateTimeField(
        help_text="Start of the rolling window that triggered the suggestion.",
    )
    window_end = models.DateTimeField(
        help_text="End of the rolling window that triggered the suggestion.",
    )
    sample_paths = models.JSONField(
        default=list,
        blank=True,
        help_text="Up to 10 example request paths that contributed to this suggestion.",
    )
    top_threat_signals = models.JSONField(
        default=list,
        blank=True,
        help_text="Most frequent threat signal codes from the requests.",
    )
    gemini_analysis = models.TextField(
        blank=True,
        default="",
        help_text="Gemini's reasoning if escalation was used.",
    )

    # ── Admin action ────────────────────────────────────────────────
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    resolved_by = models.ForeignKey(
        "accounts.Users",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_threat_suggestions",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(
        blank=True,
        default="",
        help_text="Free-text notes the admin can attach when accepting or dismissing.",
    )

    # ── Timestamps ──────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status", "-created_at"]),
            models.Index(fields=["organization", "ip_address", "-created_at"]),
        ]

    def __str__(self):
        return (
            f"ThreatSuggestion({self.ip_address}, {self.trigger_zone}, "
            f"{self.status}) [{self.request_count} hits]"
        )
