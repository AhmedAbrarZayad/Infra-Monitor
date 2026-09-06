from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


def backfill_incident_services(apps, schema_editor):
    Incident = apps.get_model("incident", "Incident")
    IncidentAlert = apps.get_model("incident", "IncidentAlert")
    Service = apps.get_model("servers", "Service")

    for incident in Incident.objects.filter(service__isnull=True).iterator():
        service_ids = set()
        links = IncidentAlert.objects.filter(incident_id=incident).select_related(
            "alert_id", "alert_id__detection_id"
        )
        for link in links:
            alert = link.alert_id
            if alert is None:
                continue
            candidates = [alert.service_id_id]
            if alert.detection_id_id:
                candidates.append(alert.detection_id.service_id_id)
            for service_id in candidates:
                valid = Service.objects.filter(
                    pk=service_id,
                    server_id__organization_id=incident.organization_id,
                )
                if incident.server_id_id:
                    valid = valid.filter(server_id_id=incident.server_id_id)
                if service_id and valid.exists():
                    service_ids.add(service_id)
        if len(service_ids) != 1:
            continue
        service_id = service_ids.pop()
        incident.service_id = service_id
        incident.save(update_fields=["service"])


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("alert", "0004_alter_alert_organization"),
        ("incident", "0005_alter_incident_organization"),
        ("servers", "0007_serviceadminassignment"),
    ]

    operations = [
        migrations.AlterField(
            model_name="incident",
            name="assigned_to",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="incident",
            name="service",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="incidents", to="servers.service"),
        ),
        migrations.RunPython(backfill_incident_services, migrations.RunPython.noop),
    ]
