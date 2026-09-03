import uuid

from django.db import models
from .servers import Servers
from django.utils import timezone
class Service(models.Model):
    service_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    server_id = models.ForeignKey(Servers, on_delete=models.CASCADE, related_name="services")
    service_name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=Servers.Status.choices, default=Servers.Status.UNKNOWN, db_index=True)
    port = models.IntegerField(null=True, blank=True)
    last_reported_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["server_id", "service_name"], name="unique_server_service_name")]
        ordering = ["display_name", "service_id"]
