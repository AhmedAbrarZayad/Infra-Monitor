import os

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Users


class Command(BaseCommand):
    help = "Create or refresh three standalone users for testing the Owner/Admin/Engineer flow."

    personas = (
        ("OWNER", "owner", "owner@example.com", "Owner123!"),
        ("ADMIN", "admin", "admin@example.com", "Admin123!"),
        ("ENGINEER", "engineer", "engineer@example.com", "Engineer123!"),
    )

    @transaction.atomic
    def handle(self, *args, **options):
        for role, default_username, default_email, default_password in self.personas:
            prefix = f"SEED_{role}"
            username = os.getenv(f"{prefix}_USERNAME", default_username).strip()
            email = os.getenv(f"{prefix}_EMAIL", default_email).strip().lower()
            password = os.getenv(f"{prefix}_PASSWORD", default_password)

            user, created = Users.objects.get_or_create(
                email=email,
                defaults={"username": username},
            )
            user.username = username
            user.role = role
            user.is_email_verified = True
            user.is_active = True
            user.set_password(password)
            user.save()

            action = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{action} {role.title()}: {email}"))

        self.stdout.write("Created users only; no organization memberships were created.")
