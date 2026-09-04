import uuid

from django.conf import settings
from django.db import models
from servers.models import Servers

from .organization import Organization


class EnrollmentToken(models.Model):
    class Stage(models.TextChoices):
        CREATED = "CREATED", "Created"
        INSTALLING = "INSTALLING", "Installing"
        CONNECTED = "CONNECTED", "Connected"
        FAILED = "FAILED", "Failed"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    class InstallerStage(models.TextChoices):
        INSTALLER_STARTED = "INSTALLER_STARTED", "Installer started"
        COLLECTOR_INSTALLED = "COLLECTOR_INSTALLED", "Collector installed"
        COLLECTOR_STARTED = "COLLECTOR_STARTED", "Collector started"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="monitoring_enrollments")
    server = models.OneToOneField(Servers, null=True, blank=True, on_delete=models.SET_NULL, related_name="monitoring_enrollment")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="created_monitoring_enrollments")
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    token_prefix = models.CharField(max_length=20, editable=False)
    server_name = models.CharField(max_length=255)
    environment = models.CharField(max_length=64)
    stage = models.CharField(max_length=16, choices=Stage.choices, default=Stage.CREATED, db_index=True)
    installer_stage = models.CharField(max_length=32, choices=InstallerStage.choices, blank=True)
    expires_at = models.DateTimeField(db_index=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    first_metric_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=64, blank=True)
    failure_message = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "id"]

    @property
    def is_used(self):
        return self.consumed_at is not None
