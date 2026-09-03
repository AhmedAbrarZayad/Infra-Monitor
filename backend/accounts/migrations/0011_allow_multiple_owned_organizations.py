from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("accounts", "0010_complete_organization_membership")]

    operations = [
        migrations.RemoveConstraint(
            model_name="organizationmembership",
            name="unique_owned_organization_per_user",
        ),
    ]
