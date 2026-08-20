from django.db import models
from servers.models.servers import Servers
from servers.models.service import Service
from django.utils import timezone
class AnomalyDetection(models.Model):
    detection_id = models.UUIDField(primary_key=True)
    server_id = models.ForeignKey(Servers, on_delete=models.SET_NULL, null=True)
    service_id = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True)
    anomaly_score = models.FloatField()
    confidence_score = models.FloatField()
    is_anomaly = models.BooleanField()
    feature_values = models.JSONField()
    window_started_at = models.DateTimeField()
    window_ended_at = models.DateTimeField()
    detected_at = models.DateTimeField(default=timezone.now)