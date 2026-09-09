import uuid

from django.conf import settings
from django.db import models


class DeviceRegistration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="device_registrations",
    )
    installation_id = models.UUIDField(unique=True)
    token = models.TextField(unique=True)
    active = models.BooleanField(default=True, db_index=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-last_seen_at"]


class SentNotification(models.Model):
    class State(models.TextChoices):
        PENDING = "PENDING"
        SENT = "SENT"
        FAILED = "FAILED"
        SKIPPED = "SKIPPED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_notifications",
    )
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE)
    event_type = models.CharField(max_length=32)
    resource_type = models.CharField(max_length=16)
    resource_id = models.UUIDField()
    deduplication_key = models.CharField(max_length=255)
    title = models.CharField(max_length=160)
    body = models.CharField(max_length=255)
    state = models.CharField(max_length=16, choices=State.choices, default=State.PENDING)
    provider_message_id = models.CharField(max_length=255, blank=True)
    provider_error = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "deduplication_key"],
                name="unique_user_notification_deduplication",
            )
        ]
        ordering = ["-created_at"]
