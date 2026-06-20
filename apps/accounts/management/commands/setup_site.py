from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from apps.branding.models import SiteBranding
from apps.statuspage.models import SystemComponent

User = get_user_model()


class Command(BaseCommand):
    help = "Initialize site branding, default components, and optional superuser"

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin")
        parser.add_argument("--email", default="admin@example.com")
        parser.add_argument("--password", default="admin123")
        parser.add_argument("--skip-superuser", action="store_true")

    def handle(self, *args, **options):
        branding = SiteBranding.get_solo()
        self.stdout.write(self.style.SUCCESS(f"Branding ready: {branding.site_name}"))

        defaults = [
            ("Web Application", "Main asset tracking application", 1),
            ("Database", "PostgreSQL database server", 2),
            ("File Storage", "Uploaded photos and documents", 3),
        ]
        for name, desc, order in defaults:
            SystemComponent.objects.get_or_create(
                name=name,
                defaults={"description": desc, "display_order": order},
            )
        self.stdout.write(self.style.SUCCESS("Default status components created."))

        if not options["skip_superuser"]:
            username = options["username"]
            if not User.objects.filter(username=username).exists():
                User.objects.create_superuser(
                    username=username,
                    email=options["email"],
                    password=options["password"],
                    role=User.Role.SUPER_USER,
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Superuser '{username}' created with role Super User.")
                )
            else:
                self.stdout.write(f"Superuser '{username}' already exists.")
