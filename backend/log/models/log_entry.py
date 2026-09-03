import uuid

from django.db import models
from accounts.models.organization import Organization
from servers.models.servers import Servers
from servers.models.service import Service
class LogEntry(models.Model):
    log_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="logs")
    server_id = models.ForeignKey(Servers, on_delete=models.CASCADE, null=True)
    service_id = models.ForeignKey(Service, on_delete=models.CASCADE, null=True)
    source = models.CharField(max_length=255)
    log_level = models.CharField(max_length=32, db_index=True)
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    logged_at = models.DateTimeField(db_index=True)
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-logged_at", "log_id"]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.server_id and self.server_id.organization_id != self.organization_id:
            raise ValidationError({"server_id": "Server must belong to this organization."})
        if self.service_id and self.service_id.server_id.organization_id != self.organization_id:
            raise ValidationError({"service_id": "Service must belong to this organization."})
