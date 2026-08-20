from django.db import models
from .servers import Servers
from .service import Service

class Metrics(models.Model):
    metric_id = models.UUIDField(primary_key=True)
    server_id = models.ForeignKey(Servers, on_delete=models.CASCADE)
    service_id = models.ForeignKey(Service, on_delete=models.CASCADE)
    metric_type = models.CharField()
    value = models.FloatField()
    unit = models.CharField()
    labels = models.JSONField()
    recorded_at = models.DateTimeField()