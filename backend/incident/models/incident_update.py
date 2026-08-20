from django.db import models 
from .incident import Incident
from accounts.models.users import Users
from django.utils import timezone
class IncidentUpdate(models.Model):
    update_id = models.UUIDField(primary_key=True)
    incident_id = models.ForeignKey(Incident, on_delete=models.CASCADE)
    user_id = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True)
    action = models.CharField()
    old_status = models.CharField()
    new_status = models.CharField()
    comment = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)    