from django.db import models 
from servers.models.servers import Servers
from servers.models.service import Service
class LogEntry(models.Model):
    log_id = models.UUIDField(primary_key=True)
    server_id = models.ForeignKey(Servers, on_delete=models.CASCADE, null=True)
    service_id = models.ForeignKey(Service, on_delete=models.CASCADE, null=True)
    source = models.CharField()
    log_level = models.CharField()
    message = models.TextField()
    metadata = models.JSONField()
    logged_at = models.DateTimeField()
    ingested_at = models.DateTimeField()