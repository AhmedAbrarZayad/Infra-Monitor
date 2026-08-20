from django.db import models
from accounts.models.users import Users
from django.utils import timezone
from incident.models.incident import Incident
class AssistantConversation(models.Model):
    conversation_id = models.UUIDField(primary_key=True)
    user_id = models.ForeignKey(Users, on_delete=models.CASCADE)
    incident_id = models.ForeignKey(Incident, on_delete=models.SET_NULL, null=True)
    title = models.CharField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
