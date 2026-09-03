import uuid

from django.db import models
from accounts.models.organization import Organization
from accounts.models.users import Users


class Servers(models.Model):
    class Status(models.TextChoices):
        HEALTHY = "HEALTHY"
        WARNING = "WARNING"
        CRITICAL = "CRITICAL"
        OFFLINE = "OFFLINE"
        STALE = "STALE"
        UNKNOWN = "UNKNOWN"

    server_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="servers")
    name = models.CharField(max_length=255)
    host_name = models.CharField(max_length=255)
    ip_address = models.CharField(max_length=255, blank=True)
    environment = models.CharField(max_length=64, db_index=True)
    os_type = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.UNKNOWN, db_index=True)
    agent_config = models.JSONField(default=dict, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True, db_index=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    registered_by = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "host_name"], name="unique_org_hostname")]
        ordering = ["name", "server_id"]
