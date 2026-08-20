from django.db import models
from servers.models.servers import Servers
from servers.models.service import Service
from django.utils import timezone
from ml_model.models.anomaly_detection import AnomalyDetection
class Alert(models.Model):
    alert_id = models.UUIDField(primary_key=True)
    server_id = models.ForeignKey(Servers, on_delete=models.SET_NULL, null=True)
    service_id = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True)
    detection_id = models.ForeignKey(AnomalyDetection, on_delete=models.SET_NULL, null=True)
    title = models.CharField()
    description = models.TextField()
    category = models.CharField()
    severity = models.CharField()
    state = models.CharField()
    fingerprint = models.CharField()
    triggered_at = models.DateTimeField(default=timezone.now)
    acknowledged_at = models.DateTimeField(default=timezone.now)
    cleared_at = models.DateTimeField(default=timezone.now)