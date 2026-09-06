import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from .anomaly_detection import AnomalyDetection


class AnomalyAssignmentEvent(models.Model):
    class Action(models.TextChoices):
        ASSIGNED = "ASSIGNED"
        REASSIGNED = "REASSIGNED"
        UNASSIGNED = "UNASSIGNED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    anomaly = models.ForeignKey(
        AnomalyDetection,
        on_delete=models.CASCADE,
        related_name="assignment_events",
    )
    action = models.CharField(max_length=16, choices=Action.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="anomaly_assignment_events_created",
    )
    previous_subject = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="anomaly_assignment_events_left",
    )
    new_subject = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="anomaly_assignment_events_received",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at", "id"]
