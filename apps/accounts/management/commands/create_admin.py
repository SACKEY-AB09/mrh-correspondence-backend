import os
from django.core.management.base import BaseCommand
from apps.accounts.models import User


class Command(BaseCommand):
    help = "Creates a superuser/admin from environment variables, if one doesn't already exist."

    def handle(self, *args, **options):
        email = os.environ.get("ADMIN_EMAIL")
        password = os.environ.get("ADMIN_PASSWORD")

        if not email or not password:
            self.stdout.write(self.style.ERROR("ADMIN_EMAIL and ADMIN_PASSWORD env vars must be set."))
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f"User {email} already exists — skipping."))
            return

        User.objects.create_superuser(
            username=email.split("@")[0],
            email=email,
            password=password,
            role=User.Role.ADMIN,
        )
        self.stdout.write(self.style.SUCCESS(f"Superuser {email} created."))