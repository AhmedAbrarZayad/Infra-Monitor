import uuid

from django.db import models
from .incident import Incident
from django.utils import timezone
from alert.models.alert import Alert
class IncidentAlert(models.Model):
    incident_alert_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident_id = models.ForeignKey(Incident, on_delete=models.CASCADE)
    alert_id = models.ForeignKey(Alert, on_delete=models.CASCADE, null=True)
    linked_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["incident_id", "alert_id"], name="unique_incident_alert")]
