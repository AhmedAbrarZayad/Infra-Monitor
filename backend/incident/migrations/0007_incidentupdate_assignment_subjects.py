from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_incident_assignment_subjects(apps, schema_editor):
    Update = apps.get_model("incident", "IncidentUpdate")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    for update in Update.objects.filter(action="ASSIGNED", new_subject__isnull=True).iterator():
        raw_id = (update.comment or "").strip()
        if raw_id.isdigit() and User.objects.filter(pk=int(raw_id)).exists():
            update.new_subject_id = int(raw_id)
            update.save(update_fields=["new_subject"])


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("incident", "0006_incident_service"),
    ]

    operations = [
        migrations.AddField(
            model_name="incidentupdate",
            name="new_subject",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="incident_assignment_events_received", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="incidentupdate",
            name="previous_subject",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="incident_assignment_events_left", to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(backfill_incident_assignment_subjects, migrations.RunPython.noop),
    ]
