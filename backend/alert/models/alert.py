import uuid

from django.conf import settings
from django.db import models
from accounts.models.organization import Organization
from servers.models.servers import Servers
from servers.models.service import Service
from django.utils import timezone
from ml_model.models.anomaly_detection import AnomalyDetection
class Alert(models.Model):
    class Severity(models.TextChoices):
        CRITICAL = "CRITICAL"
        HIGH = "HIGH"
        WARNING = "WARNING"
        INFO = "INFO"
    class State(models.TextChoices):
        ACTIVE = "ACTIVE"
        ACKNOWLEDGED = "ACKNOWLEDGED"
        RESOLVED = "RESOLVED"

    alert_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="alerts")
    server_id = models.ForeignKey(Servers, on_delete=models.SET_NULL, null=True)
    service_id = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True)
    detection_id = models.ForeignKey(AnomalyDetection, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=128)
    severity = models.CharField(max_length=16, choices=Severity.choices, db_index=True)
    state = models.CharField(max_length=16, choices=State.choices, default=State.ACTIVE, db_index=True)
    fingerprint = models.CharField(max_length=255)
    triggered_at = models.DateTimeField(default=timezone.now)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    cleared_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="acknowledged_alerts")
    cleared_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="resolved_alerts")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "fingerprint"], condition=models.Q(state__in=["ACTIVE", "ACKNOWLEDGED"]), name="unique_open_alert_fingerprint")]
        ordering = ["-triggered_at", "alert_id"]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.server_id and self.server_id.organization_id != self.organization_id:
            raise ValidationError({"server_id": "Server must belong to this organization."})
        if self.service_id and self.service_id.server_id.organization_id != self.organization_id:
            raise ValidationError({"service_id": "Service must belong to this organization."})
        if self.detection_id and self.detection_id.organization_id != self.organization_id:
            raise ValidationError({"detection_id": "Detection must belong to this organization."})
