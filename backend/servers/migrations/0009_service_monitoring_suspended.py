from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("servers", "0008_serviceadminassignmentevent"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="monitoring_suspended",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="service",
            name="monitoring_suspended_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
