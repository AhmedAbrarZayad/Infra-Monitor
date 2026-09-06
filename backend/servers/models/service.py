import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from accounts.models.organization_membership import OrganizationMembership

from .servers import Servers


class Service(models.Model):
    service_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    server_id = models.ForeignKey(Servers, on_delete=models.CASCADE, related_name="services")
    service_name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=Servers.Status.choices, default=Servers.Status.UNKNOWN, db_index=True)
    port = models.IntegerField(null=True, blank=True)
    last_reported_at = models.DateTimeField(null=True, blank=True, db_index=True)
    status_changed_at = models.DateTimeField(null=True, blank=True)
    lifecycle_reason = models.CharField(max_length=64, default="awaiting_telemetry")
    consecutive_failure_observations = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["server_id", "service_name"], name="unique_server_service_name")]
        ordering = ["display_name", "service_id"]


class ServiceAdminAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="admin_assignments"
    )
    membership = models.ForeignKey(
        OrganizationMembership,
        on_delete=models.CASCADE,
        related_name="service_admin_assignments",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="service_admin_assignments_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["service", "membership"],
                name="unique_service_admin_assignment",
            )
        ]

    def clean(self):
        errors = {}
        if (
            self.service_id
            and self.membership_id
            and self.service.server_id.organization_id
            != self.membership.organization_id
        ):
            errors["membership"] = "Membership must belong to the service organization."
        if self.membership_id and (
            not self.membership.approved
            or self.membership.role != OrganizationMembership.RoleEnum.ADMIN
        ):
            errors["membership"] = "Only an approved Admin membership may be assigned."
        if self.assigned_by_id and self.service_id and not OrganizationMembership.objects.filter(
            organization_id=self.service.server_id.organization_id,
            user_id=self.assigned_by_id,
            approved=True,
            role=OrganizationMembership.RoleEnum.OWNER,
        ).exists():
            errors["assigned_by"] = "Assigning user must be the approved organization Owner."
        if errors:
            raise ValidationError(errors)


class ServiceAdminAssignmentEvent(models.Model):
    class Action(models.TextChoices):
        ASSIGNED = "ASSIGNED"
        UNASSIGNED = "UNASSIGNED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="admin_assignment_events"
    )
    action = models.CharField(max_length=16, choices=Action.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="service_admin_assignment_events_created",
    )
    previous_subject = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_admin_unassignment_events",
    )
    new_subject = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_admin_assignment_events",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at", "id"]
