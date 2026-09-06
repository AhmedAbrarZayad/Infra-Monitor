import uuid

from django.conf import settings
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
    service_id = models.ForeignKey(
        Service, on_delete=models.SET_NULL, null=True, related_name="anomaly_detections"
    )
    anomaly_score = models.FloatField()
    confidence_score = models.FloatField()
    is_anomaly = models.BooleanField()
    feature_values = models.JSONField(default=dict)
    model_version = models.CharField(max_length=64, default="legacy")
    window_started_at = models.DateTimeField()
    window_ended_at = models.DateTimeField()
    detected_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_anomalies",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_anomalies",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="anomaly_assignments_created",
    )
    assigned_at = models.DateTimeField(null=True, blank=True)

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
        from accounts.models import OrganizationMembership

        errors = {}
        if self.server_id and self.server_id.organization_id != self.organization_id:
            errors["server_id"] = "Server must belong to this organization."
        if self.service_id and self.service_id.server_id.organization_id != self.organization_id:
            errors["service_id"] = "Service must belong to this organization."
        if self.service_id and self.server_id_id and self.service_id.server_id_id != self.server_id_id:
            errors["service_id"] = "Service must belong to the detection server."
        if self.assigned_to_id and not OrganizationMembership.objects.filter(
            organization_id=self.organization_id,
            user_id=self.assigned_to_id,
            approved=True,
            role=OrganizationMembership.RoleEnum.ENGINEER,
        ).exists():
            errors["assigned_to"] = "Assignee must be an approved Engineer in this organization."
        if self.assigned_by_id and not OrganizationMembership.objects.filter(
            organization_id=self.organization_id,
            user_id=self.assigned_by_id,
            approved=True,
            role__in=[
                OrganizationMembership.RoleEnum.OWNER,
                OrganizationMembership.RoleEnum.ADMIN,
            ],
        ).exists():
            errors["assigned_by"] = "Assigning user must be an approved Owner or Admin in this organization."
        if errors:
            raise ValidationError(errors)
