# Generated for trusted VictoriaMetrics tenancy and installer progress.

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0013_enrollmenttoken")]

    operations = [
        migrations.AddField(
            model_name="enrollmenttoken",
            name="installer_stage",
            field=models.CharField(
                blank=True,
                choices=[
                    ("INSTALLER_STARTED", "Installer started"),
                    ("COLLECTOR_INSTALLED", "Collector installed"),
                    ("COLLECTOR_STARTED", "Collector started"),
                    ("FAILED", "Failed"),
                ],
                max_length=32,
            ),
        ),
        migrations.CreateModel(
            name="VictoriaMetricsTenant",
            fields=[
                ("account_id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "project_id",
                    models.PositiveBigIntegerField(
                        default=0,
                        validators=[django.core.validators.MaxValueValidator(4294967295)],
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "organization",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="victoriametrics_tenant",
                        to="accounts.organization",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="victoriametricstenant",
            constraint=models.CheckConstraint(
                condition=models.Q(("account_id__lte", 4294967295)),
                name="victoriametrics_account_id_uint32",
            ),
        ),
        migrations.AddConstraint(
            model_name="victoriametricstenant",
            constraint=models.CheckConstraint(
                condition=models.Q(("project_id__lte", 4294967295)),
                name="victoriametrics_project_id_uint32",
            ),
        ),
    ]
