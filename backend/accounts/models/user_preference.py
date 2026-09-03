import uuid

from django.db import models
from .users import Users
from django.utils import timezone as django_timezone
class UserPreference(models.Model):
    preference_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.OneToOneField(Users, on_delete=models.CASCADE, related_name="preferences")
    notifications_enabled = models.BooleanField(default=False)
    refresh_interval_seconds = models.IntegerField(default=10)
    timezone = models.CharField(max_length=64, default="UTC")
    theme = models.CharField(max_length=16, default="dark")
    default_environment = models.CharField(max_length=64, default="production")
    updated_at = models.DateTimeField(auto_now=True)
