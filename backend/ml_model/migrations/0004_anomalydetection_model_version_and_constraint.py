from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ml_model", "0003_alter_anomalydetection_organization"),
    ]

    operations = [
        migrations.AddField(
            model_name="anomalydetection",
            name="model_version",
            field=models.CharField(default="legacy", max_length=64),
        ),
        migrations.AddConstraint(
            model_name="anomalydetection",
            constraint=models.UniqueConstraint(
                fields=(
                    "service_id",
                    "window_started_at",
                    "window_ended_at",
                    "model_version",
                ),
                name="unique_service_model_detection_window",
            ),
        ),
    ]
