import uuid

from django.db import models


class ShieldConfig(models.Model):
    """Per-organization configuration for the Request Shield feature.

    Controls whether classification is active, whether Gemini escalation is
    enabled for gray-zone requests, and the thresholds that trigger threat
    suggestions to the admin.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="shield_config",
    )

    # ── Feature toggles ─────────────────────────────────────────────
    enabled = models.BooleanField(
        default=True,
        help_text="Master switch: when off, incoming request logs are stored but not classified.",
    )
    gemini_escalation = models.BooleanField(
        default=True,
        help_text="Send GRAY-zone requests to Gemini for deeper analysis.",
    )
    platform_self_monitor = models.BooleanField(
        default=True,
        help_text="Also classify requests arriving at the Infra-Monitor platform API.",
    )

    # ── Suggestion thresholds ───────────────────────────────────────
    red_suggestion_threshold = models.IntegerField(
        default=5,
        help_text="Number of RED requests from an IP before generating a threat suggestion.",
    )
    gray_suggestion_threshold = models.IntegerField(
        default=20,
        help_text="Number of GRAY requests from an IP before generating a threat suggestion.",
    )
    suggestion_window_minutes = models.IntegerField(
        default=60,
        help_text="Rolling window (in minutes) for counting per-IP zone hits.",
    )

    # ── Notification ────────────────────────────────────────────────
    notify_on_red = models.BooleanField(
        default=True,
        help_text="Send an in-app notification when a threat suggestion is created.",
    )

    # ── Timestamps ──────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shield Configuration"
        verbose_name_plural = "Shield Configurations"

    def __str__(self):
        state = "enabled" if self.enabled else "disabled"
        return f"ShieldConfig({self.organization}) [{state}]"
