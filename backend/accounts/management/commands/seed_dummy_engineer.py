import os

from django.core.management.base import BaseCommand

from accounts.models import Users


class Command(BaseCommand):
    help = "Create or refresh the local dummy engineer account without an organization membership."

    def handle(self, *args, **options):
        username = os.getenv("SEED_ENGINEER_USERNAME", "engineer")
        email = os.getenv("SEED_ENGINEER_EMAIL", "engineer@example.com").strip().lower()
        password = os.getenv("SEED_ENGINEER_PASSWORD", "Engineer123!")

        user, created = Users.objects.get_or_create(
            email=email,
            defaults={"username": username},
        )
        user.username = username
        user.role = "ENGINEER"
        user.is_email_verified = True
        user.is_active = True
        user.set_password(password)
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} dummy engineer: {email}"))
        self.stdout.write("No organization membership was created.")
