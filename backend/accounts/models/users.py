from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class Users(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, default="viewer")
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Use email as the login identifier
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email
