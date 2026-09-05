import uuid

from django.db import models
from django.utils import timezone

from .assistant_conversation import AssistantConversation


class AssistantMessage(models.Model):
    class Sender(models.TextChoices):
        USER = "USER", "User"
        ASSISTANT = "ASSISTANT", "Assistant"

    message_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation_id = models.ForeignKey(AssistantConversation, on_delete=models.CASCADE, null=True)
    sender_type = models.CharField(max_length=16, choices=Sender.choices)
    message = models.TextField()
    evidence = models.JSONField(default=list, blank=True)
    client_message_id = models.UUIDField(null=True, blank=True)
    response_to_client_message_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at", "message_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation_id", "client_message_id"],
                name="unique_conversation_client_message",
            ),
            models.UniqueConstraint(
                fields=["conversation_id", "response_to_client_message_id"],
                name="unique_conversation_assistant_response",
            ),
        ]
