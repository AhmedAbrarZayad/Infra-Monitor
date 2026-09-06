import uuid

from django.db import models

from accounts.models.users import Users

from .incident import Incident


class IncidentUpdate(models.Model):
    update_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident_id = models.ForeignKey(Incident, on_delete=models.CASCADE)
    user_id = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True)
    previous_subject = models.ForeignKey(
        Users,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incident_assignment_events_left",
    )
    new_subject = models.ForeignKey(
        Users,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incident_assignment_events_received",
    )
    action = models.CharField(max_length=64)
    old_status = models.CharField(max_length=16, blank=True)
    new_status = models.CharField(max_length=16, blank=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "update_id"]
