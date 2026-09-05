import uuid

from django.db import models
from django.utils import timezone

from accounts.models.organization import Organization
from accounts.models.users import Users

from .assistant_conversation import AssistantConversation


class AssistantWebSocketTicket(models.Model):
    ticket_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token_hash = models.CharField(max_length=64, unique=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    conversation = models.ForeignKey(AssistantConversation, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
