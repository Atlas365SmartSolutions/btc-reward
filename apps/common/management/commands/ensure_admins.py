from __future__ import annotations

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Create or update Django admin users without committing credentials."

    def add_arguments(self, parser):
        parser.add_argument(
            "--admin",
            action="append",
            default=[],
            metavar="USERNAME:EMAIL",
            help="Admin identity to create or update. Can be passed more than once.",
        )
        parser.add_argument(
            "--password",
            default=None,
            help="Password to set. Prefer ADMIN_BOOTSTRAP_PASSWORD in shells and deploy systems.",
        )
        parser.add_argument(
            "--remove-username",
            action="append",
            default=[],
            help="Username to delete after the requested admins are ensured.",
        )

    def handle(self, *args, **options):
        password = options["password"] or os.getenv("ADMIN_BOOTSTRAP_PASSWORD")
        admins = options["admin"]
        if not admins:
            raise CommandError("Pass at least one --admin USERNAME:EMAIL value.")
        if not password:
            raise CommandError("Set ADMIN_BOOTSTRAP_PASSWORD or pass --password.")

        user_model = get_user_model()
        with transaction.atomic():
            for raw_admin in admins:
                username, email = self._parse_admin(raw_admin)
                email_conflict = (
                    user_model.objects.filter(email__iexact=email).exclude(username__iexact=username).first()
                )
                if email_conflict is not None:
                    raise CommandError(f"Email {email} is already assigned to another user.")

                user, created = user_model.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": email,
                        "is_staff": True,
                        "is_superuser": True,
                        "is_active": True,
                    },
                )
                user.email = email
                user.is_staff = True
                user.is_superuser = True
                user.is_active = True
                user.set_password(password)
                user.save(
                    update_fields=[
                        "email",
                        "is_staff",
                        "is_superuser",
                        "is_active",
                        "password",
                    ]
                )
                self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Updated'} admin {username}"))

            for username in options["remove_username"]:
                deleted, _ = user_model.objects.filter(username=username).delete()
                if deleted:
                    self.stdout.write(self.style.WARNING(f"Removed admin/user {username}"))

    def _parse_admin(self, raw_admin: str) -> tuple[str, str]:
        try:
            username, email = raw_admin.split(":", maxsplit=1)
        except ValueError as exc:
            raise CommandError("--admin must be formatted as USERNAME:EMAIL") from exc

        username = username.strip()
        email = email.strip().lower()
        if not username or "@" not in email:
            raise CommandError("--admin must include a non-empty username and valid email.")
        return username, email
