import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0014_monitoring_tenant_and_installer_stage"),
        ("servers", "0006_service_lifecycle_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="ServiceAdminAssignment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assigned_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="service_admin_assignments_created", to=settings.AUTH_USER_MODEL)),
                ("membership", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="service_admin_assignments", to="accounts.organizationmembership")),
                ("service", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="admin_assignments", to="servers.service")),
            ],
            options={
                "ordering": ["created_at", "id"],
                "constraints": [models.UniqueConstraint(fields=("service", "membership"), name="unique_service_admin_assignment")],
            },
        ),
    ]
