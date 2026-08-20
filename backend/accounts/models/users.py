from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
class Users(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
