import uuid

from django.db import models
from django.utils import timezone

from accounts.models.organization import Organization
from servers.models.servers import Servers
from servers.models.service import Service


class AnomalyDetection(models.Model):
    detection_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="anomaly_detections"
    )
    server_id = models.ForeignKey(Servers, on_delete=models.SET_NULL, null=True)
    service_id = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True)
    anomaly_score = models.FloatField()
    confidence_score = models.FloatField()
    is_anomaly = models.BooleanField()
    feature_values = models.JSONField(default=dict)
    model_version = models.CharField(max_length=64, default="legacy")
    window_started_at = models.DateTimeField()
    window_ended_at = models.DateTimeField()
    detected_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-detected_at", "detection_id"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "service_id",
                    "window_started_at",
                    "window_ended_at",
                    "model_version",
                ],
                name="unique_service_model_detection_window",
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.server_id and self.server_id.organization_id != self.organization_id:
            raise ValidationError({"server_id": "Server must belong to this organization."})
        if self.service_id and self.service_id.server_id.organization_id != self.organization_id:
            raise ValidationError({"service_id": "Service must belong to this organization."})
