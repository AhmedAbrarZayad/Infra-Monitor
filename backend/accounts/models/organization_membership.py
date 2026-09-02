from django.db import models
from .users import Users
from django_enum import EnumField
from datetime import datetime
from django.utils import timezone
class OrganizationMembership(models.Model):
    class RoleEnum(models.TextChoices):
        OWNER = 'OWNER', 'Owner of the organization'
        ADMIN = 'ADMIN', 'Admins assigned by owners of the organization'
        ENGINEER = 'ENGINEER', 'Engineers assigned by owners or admins of the organization'
    id = models.UUIDField(primary_key=True)
    # organization foreign key
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    role = EnumField(RoleEnum, null=False, blank=False, default=RoleEnum.ENGINEER)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField()