import uuid

from django.conf import settings
from django.db import models

from .servers import Servers


class MonitoringConnection(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONNECTED = "CONNECTED", "Connected"
        DEGRADED = "DEGRADED", "Degraded"
        DISCONNECTED = "DISCONNECTED", "Disconnected"

    class IngestionHealth(models.TextChoices):
        UNKNOWN = "UNKNOWN", "Unknown"
        HEALTHY = "HEALTHY", "Healthy"
        DEGRADED = "DEGRADED", "Degraded"
        STOPPED = "STOPPED", "Stopped"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    server = models.OneToOneField(Servers, on_delete=models.CASCADE, related_name="monitoring_connection")
    connection_method = models.CharField(max_length=32, default="REMOTE_WRITE")
    collector = models.CharField(max_length=64, blank=True)
    collector_version = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    ingestion_health = models.CharField(max_length=16, choices=IngestionHealth.choices, default=IngestionHealth.UNKNOWN)
    last_callback_at = models.DateTimeField(null=True, blank=True)
    last_metric_at = models.DateTimeField(null=True, blank=True)
    disconnected_at = models.DateTimeField(null=True, blank=True)
    disconnected_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="disconnected_monitoring_connections")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ServerWriteCredential(models.Model):
    class State(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        GRACE = "GRACE", "Grace"
        REVOKED = "REVOKED", "Revoked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(MonitoringConnection, on_delete=models.CASCADE, related_name="credentials")
    secret_hash = models.CharField(max_length=64, editable=False)
    state = models.CharField(max_length=16, choices=State.choices, default=State.ACTIVE, db_index=True)
    valid_until = models.DateTimeField(null=True, blank=True, db_index=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_server_write_credentials")
    rotation_key = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "id"]
        constraints = [
            models.UniqueConstraint(fields=["connection", "rotation_key"], condition=models.Q(rotation_key__isnull=False), name="unique_connection_rotation_key"),
            models.UniqueConstraint(fields=["connection"], condition=models.Q(state="ACTIVE"), name="unique_active_server_credential"),
        ]
