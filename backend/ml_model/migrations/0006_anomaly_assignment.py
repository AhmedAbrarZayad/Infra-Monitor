from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ml_model", "0005_anomalydetection_resolution"),
    ]

    operations = [
        migrations.AlterField(
            model_name="anomalydetection",
            name="service_id",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="anomaly_detections", to="servers.service"),
        ),
        migrations.AddField(
            model_name="anomalydetection",
            name="assigned_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="anomalydetection",
            name="assigned_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="anomaly_assignments_created", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="anomalydetection",
            name="assigned_to",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_anomalies", to=settings.AUTH_USER_MODEL),
        ),
    ]
