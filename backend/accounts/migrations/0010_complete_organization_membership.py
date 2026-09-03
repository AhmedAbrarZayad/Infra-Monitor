import uuid

import django.db.models.deletion
from django.db import migrations, models


def require_empty_draft_memberships(apps, schema_editor):
    membership = apps.get_model("accounts", "OrganizationMembership")
    if membership.objects.exists():
        raise RuntimeError(
            "OrganizationMembership contains draft rows without an organization. "
            "Assign or remove those rows before applying this migration."
        )


class Migration(migrations.Migration):
    dependencies = [("accounts", "0009_alter_organization_created_at_and_more")]

    operations = [
        migrations.AddField(
            model_name="organizationmembership",
            name="organization",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="memberships",
                to="accounts.organization",
            ),
        ),
        migrations.RunPython(require_empty_draft_memberships, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="organizationmembership",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="memberships",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name="organization",
            name="name",
            field=models.TextField(db_index=True),
        ),
        migrations.AlterField(
            model_name="organization",
            name="logo_url",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="organization",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="organization",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="organizationmembership",
            name="id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name="organizationmembership",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="organization_memberships",
                to="accounts.users",
            ),
        ),
        migrations.AlterField(
            model_name="organizationmembership",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="organizationmembership",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterModelOptions(
            name="organization",
            options={"ordering": ["name", "id"]},
        ),
        migrations.AlterModelOptions(
            name="organizationmembership",
            options={"ordering": ["-updated_at", "id"]},
        ),
        migrations.AddConstraint(
            model_name="organizationmembership",
            constraint=models.UniqueConstraint(
                fields=("organization", "user"), name="unique_organization_user_membership"
            ),
        ),
        migrations.AddConstraint(
            model_name="organizationmembership",
            constraint=models.UniqueConstraint(
                condition=models.Q(("role", "OWNER")),
                fields=("organization",),
                name="unique_owner_per_organization",
            ),
        ),
        migrations.AddConstraint(
            model_name="organizationmembership",
            constraint=models.UniqueConstraint(
                condition=models.Q(("role", "OWNER")),
                fields=("user",),
                name="unique_owned_organization_per_user",
            ),
        ),
        migrations.AddConstraint(
            model_name="organizationmembership",
            constraint=models.CheckConstraint(
                condition=models.Q(("role", "ENGINEER"), ("approved", True), _connector="OR"),
                name="privileged_memberships_are_approved",
            ),
        ),
    ]
