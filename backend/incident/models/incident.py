import uuid

from django.db import models
from accounts.models.organization import Organization
from accounts.models.users import Users
from django.utils import timezone
from servers.models.servers import Servers
class Incident(models.Model):
    class Status(models.TextChoices):
        NEW = "NEW"
        ACKNOWLEDGED = "ACKNOWLEDGED"
        INVESTIGATING = "INVESTIGATING"
        RESOLVED = "RESOLVED"
    class Severity(models.TextChoices):
        CRITICAL = "CRITICAL"
        HIGH = "HIGH"
        WARNING = "WARNING"
        INFO = "INFO"

    incident_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="incidents")
    incident_code = models.CharField(max_length=64)
    server_id = models.ForeignKey(Servers, on_delete=models.SET_NULL, null=True)
    assigned_to = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True)
    title = models.CharField()
    description = models.TextField()
    category = models.CharField(max_length=128)
    severity = models.CharField(max_length=16, choices=Severity.choices, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW, db_index=True)
    detected_at = models.DateTimeField(default=timezone.now)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "incident_code"], name="unique_org_incident_code")]
        ordering = ["-detected_at", "incident_id"]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.server_id and self.server_id.organization_id != self.organization_id:
            raise ValidationError({"server_id": "Server must belong to this organization."})
