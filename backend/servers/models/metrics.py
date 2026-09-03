import uuid

from django.db import models
from .servers import Servers
from .service import Service

class Metrics(models.Model):
    metric_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    server_id = models.ForeignKey(Servers, on_delete=models.CASCADE, related_name="metrics")
    service_id = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="metrics", null=True, blank=True)
    metric_type = models.CharField(max_length=128, db_index=True)
    value = models.FloatField()
    unit = models.CharField(max_length=64)
    labels = models.JSONField(default=dict, blank=True)
    recorded_at = models.DateTimeField(db_index=True)

    class Meta:
        indexes = [models.Index(fields=["server_id", "metric_type", "recorded_at"]), models.Index(fields=["service_id", "metric_type", "recorded_at"])]
        ordering = ["recorded_at", "metric_id"]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.service_id_id and self.service_id.server_id_id != self.server_id_id:
            raise ValidationError({"service_id": "Service must belong to the selected server."})
