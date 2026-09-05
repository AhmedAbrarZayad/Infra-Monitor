from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ml_model", "0004_anomalydetection_model_version_and_constraint"),
    ]

    operations = [
        migrations.AddField(
            model_name="anomalydetection",
            name="resolved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="anomalydetection",
            name="resolved_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="resolved_anomalies",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
