from django.db import models
from .users import Users
from django.utils import timezone as django_timezone
class UserPreference(models.Model):
    preference_id = models.UUIDField(primary_key=True)
    user_id = models.ForeignKey(Users, on_delete=models.CASCADE)
    notifications_enabled = models.BooleanField(default=False)
    refresh_interval_seconds = models.IntegerField(default=10)
    timezone = models.CharField()
    updated_at = models.DateTimeField(default=django_timezone.now)
