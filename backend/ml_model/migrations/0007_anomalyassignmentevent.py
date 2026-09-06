import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


def backfill_anomaly_assignment_events(apps, schema_editor):
    Detection = apps.get_model("ml_model", "AnomalyDetection")
    Event = apps.get_model("ml_model", "AnomalyAssignmentEvent")
    Event.objects.bulk_create(
        [
            Event(
                anomaly_id=item.pk,
                action="ASSIGNED",
                actor_id=item.assigned_by_id,
                new_subject_id=item.assigned_to_id,
                created_at=item.assigned_at or item.detected_at,
            )
            for item in Detection.objects.filter(assigned_to__isnull=False).iterator()
        ]
    )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ml_model", "0006_anomaly_assignment"),
    ]

    operations = [
        migrations.CreateModel(
            name="AnomalyAssignmentEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(choices=[("ASSIGNED", "Assigned"), ("REASSIGNED", "Reassigned"), ("UNASSIGNED", "Unassigned")], max_length=16)),
                ("created_at", models.DateTimeField(default=timezone.now)),
                ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="anomaly_assignment_events_created", to=settings.AUTH_USER_MODEL)),
                ("anomaly", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assignment_events", to="ml_model.anomalydetection")),
                ("new_subject", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="anomaly_assignment_events_received", to=settings.AUTH_USER_MODEL)),
                ("previous_subject", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="anomaly_assignment_events_left", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at", "id"]},
        ),
        migrations.RunPython(backfill_anomaly_assignment_events, migrations.RunPython.noop),
    ]
