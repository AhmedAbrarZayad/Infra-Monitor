from django.db import models
from accounts.models.users import Users
from django.utils import timezone
from servers.models.servers import Servers
class Incident(models.Model):
    incident_id = models.UUIDField(primary_key=True)
    incident_code = models.CharField()
    server_id = models.ForeignKey(Servers, on_delete=models.SET_NULL, null=True)
    assigned_to = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True)
    title = models.CharField()
    description = models.TextField()
    category = models.CharField()
    severity = models.CharField()
    status = models.CharField()
    detected_at = models.DateTimeField(default=timezone.now)
    acknowledged_at = models.DateTimeField()
    resolved_at = models.DateTimeField()
    resolution_notes = models.TextField()
