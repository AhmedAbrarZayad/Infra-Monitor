from django.db import models
from .servers import Servers
from django.utils import timezone
class Service(models.Model):
    service_id = models.UUIDField(primary_key=True)
    server_id = models.ForeignKey(Servers, on_delete=models.CASCADE)
    service_name = models.CharField()
    display_name = models.CharField()
    status = models.CharField()
    port = models.IntegerField()
    last_reported_at = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)