from django.db import models
from .assistant_conversation import AssistantConversation
class AssistantMessage(models.Model):
    message_id = models.UUIDField(primary_key=True)
    conversation_id = models.ForeignKey(AssistantConversation, on_delete=models.CASCADE, null=True)
    sender_type = models.CharField()
    message = models.CharField()
    evidence = models.JSONField()
    created_at = models.DateTimeField()