import uuid

from django.core.validators import MaxValueValidator
from django.db import models


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField(db_index=True)
    summary = models.TextField()
    logo_url = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]


class VictoriaMetricsTenant(models.Model):
    """Trusted numeric VictoriaMetrics tenant assigned to one organization."""

    account_id = models.BigAutoField(primary_key=True)
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="victoriametrics_tenant",
    )
    project_id = models.PositiveBigIntegerField(
        default=0,
        validators=[MaxValueValidator(4_294_967_295)],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(account_id__lte=4_294_967_295),
                name="victoriametrics_account_id_uint32",
            ),
            models.CheckConstraint(
                condition=models.Q(project_id__lte=4_294_967_295),
                name="victoriametrics_project_id_uint32",
            ),
        ]
