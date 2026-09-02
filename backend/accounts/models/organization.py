from django.db import models
from datetime import datetime
from django.utils import timezone
class Organization(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.TextField()
    summary = models.TextField()
    logo_url = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField()