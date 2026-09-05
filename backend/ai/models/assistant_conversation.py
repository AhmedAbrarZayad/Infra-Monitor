import uuid

from django.db import models
from django.db.models import Q
from django.utils import timezone

from accounts.models.organization import Organization
from accounts.models.users import Users
from incident.models.incident import Incident
from ml_model.models import AnomalyDetection


class AssistantConversation(models.Model):
    conversation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="assistant_conversations",
        null=True,
        blank=True,
    )
    user_id = models.ForeignKey(
        Users, on_delete=models.CASCADE, related_name="assistant_conversations"
    )
    incident_id = models.ForeignKey(Incident, on_delete=models.SET_NULL, null=True)
    anomaly = models.ForeignKey(
        AnomalyDetection,
        on_delete=models.SET_NULL,
        related_name="assistant_conversations",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "conversation_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user_id", "anomaly"],
                condition=Q(anomaly__isnull=False),
                name="unique_user_anomaly_conversation",
            )
        ]
