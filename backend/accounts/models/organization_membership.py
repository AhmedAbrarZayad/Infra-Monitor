import uuid

from django.db import models
from django_enum import EnumField

from .organization import Organization
from .users import Users


class OrganizationMembership(models.Model):
    class RoleEnum(models.TextChoices):
        OWNER = 'OWNER', 'Owner of the organization'
        ADMIN = 'ADMIN', 'Admins assigned by owners of the organization'
        ENGINEER = 'ENGINEER', 'Engineers assigned by owners or admins of the organization'
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )
    role = EnumField(RoleEnum, null=False, blank=False, default=RoleEnum.ENGINEER)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="unique_organization_user_membership",
            ),
            models.UniqueConstraint(
                fields=["organization"],
                condition=models.Q(role="OWNER"),
                name="unique_owner_per_organization",
            ),
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(role="OWNER"),
                name="unique_owned_organization_per_user",
            ),
            models.CheckConstraint(
                condition=models.Q(role="ENGINEER") | models.Q(approved=True),
                name="privileged_memberships_are_approved",
            ),
        ]
