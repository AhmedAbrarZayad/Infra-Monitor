import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


def backfill_service_admin_events(apps, schema_editor):
    Assignment = apps.get_model("servers", "ServiceAdminAssignment")
    Event = apps.get_model("servers", "ServiceAdminAssignmentEvent")
    Event.objects.bulk_create(
        [
            Event(
                service_id=item.service_id,
                action="ASSIGNED",
                actor_id=item.assigned_by_id,
                new_subject_id=item.membership.user_id,
                created_at=item.created_at,
            )
            for item in Assignment.objects.select_related("membership").iterator()
        ]
    )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("servers", "0007_serviceadminassignment"),
    ]

    operations = [
        migrations.CreateModel(
            name="ServiceAdminAssignmentEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(choices=[("ASSIGNED", "Assigned"), ("UNASSIGNED", "Unassigned")], max_length=16)),
                ("created_at", models.DateTimeField(default=timezone.now)),
                ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="service_admin_assignment_events_created", to=settings.AUTH_USER_MODEL)),
                ("new_subject", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="service_admin_assignment_events", to=settings.AUTH_USER_MODEL)),
                ("previous_subject", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="service_admin_unassignment_events", to=settings.AUTH_USER_MODEL)),
                ("service", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="admin_assignment_events", to="servers.service")),
            ],
            options={"ordering": ["-created_at", "id"]},
        ),
        migrations.RunPython(backfill_service_admin_events, migrations.RunPython.noop),
    ]
