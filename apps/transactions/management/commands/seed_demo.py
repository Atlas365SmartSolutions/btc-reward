from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.transactions.services.demo_seed import seed_demo_data


class Command(BaseCommand):
    help = "Seed deterministic demo records for local development."

    def handle(self, *args, **options):
        result = seed_demo_data()
        self.stdout.write("Seeded demo data:")
        for key, value in result.items():
            self.stdout.write(f"- {key}: {value}")
