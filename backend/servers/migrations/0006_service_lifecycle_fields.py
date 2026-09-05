from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("servers", "0005_serverwritecredential_unique_active_server_credential")]

    operations = [
        migrations.AddField(
            model_name="service",
            name="consecutive_failure_observations",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="service",
            name="lifecycle_reason",
            field=models.CharField(default="awaiting_telemetry", max_length=64),
        ),
        migrations.AddField(
            model_name="service",
            name="status_changed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
