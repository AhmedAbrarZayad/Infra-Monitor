import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0014_monitoring_tenant_and_installer_stage"),
    ]
    operations = [
        migrations.CreateModel(
            name="DeviceRegistration",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("installation_id", models.UUIDField(unique=True)),
                ("token", models.TextField(unique=True)),
                ("active", models.BooleanField(db_index=True, default=True)),
                ("last_seen_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="device_registrations", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-last_seen_at"]},
        ),
        migrations.CreateModel(
            name="SentNotification",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("event_type", models.CharField(max_length=32)),
                ("resource_type", models.CharField(max_length=16)),
                ("resource_id", models.UUIDField()),
                ("deduplication_key", models.CharField(max_length=255)),
                ("title", models.CharField(max_length=160)),
                ("body", models.CharField(max_length=255)),
                ("state", models.CharField(choices=[("PENDING", "Pending"), ("SENT", "Sent"), ("FAILED", "Failed"), ("SKIPPED", "Skipped")], default="PENDING", max_length=16)),
                ("provider_message_id", models.CharField(blank=True, max_length=255)),
                ("provider_error", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="accounts.organization")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sent_notifications", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="sentnotification",
            constraint=models.UniqueConstraint(fields=("user", "deduplication_key"), name="unique_user_notification_deduplication"),
        ),
    ]
