from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from careconnect_v2_api.models import GreenChoiceStaffProfile


MANAGER_FULL_NAME = "GreenChoice Manager"
MANAGER_EMAIL = "manager@greenchoice.local"
MANAGER_PASSWORD = "ChangeMe123!"


class Command(BaseCommand):
    help = "Seed the first GreenChoice development manager account."

    def handle(self, *args, **options):
        User = get_user_model()
        first_name, last_name = MANAGER_FULL_NAME.split(" ", 1)

        with transaction.atomic():
            user = User.objects.filter(email__iexact=MANAGER_EMAIL).first()
            created = False
            if not user:
                user, created = User.objects.get_or_create(
                    username=MANAGER_EMAIL,
                    defaults={
                        "email": MANAGER_EMAIL,
                        "first_name": first_name,
                        "last_name": last_name,
                        "is_active": True,
                    },
                )

            user.username = MANAGER_EMAIL
            user.email = MANAGER_EMAIL
            user.first_name = first_name
            user.last_name = last_name
            user.is_active = True
            user.set_password(MANAGER_PASSWORD)
            user.save(update_fields=["username", "email", "first_name", "last_name", "is_active", "password"])

            GreenChoiceStaffProfile.objects.update_or_create(
                user=user,
                defaults={"role": GreenChoiceStaffProfile.Role.MANAGER},
            )

        status = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"GreenChoice staff seed completed. Development manager {status}."))
        self.stdout.write("")
        self.stdout.write("Development Manager Login:")
        self.stdout.write(f"Email: {MANAGER_EMAIL}")
        self.stdout.write(f"Password: {MANAGER_PASSWORD}")
        self.stdout.write(f"Role: {GreenChoiceStaffProfile.Role.MANAGER}")
        self.stdout.write("")
        self.stdout.write("Use this account to log in at:")
        self.stdout.write("http://localhost:3000/login")
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("IMPORTANT:"))
        self.stdout.write("These credentials are only for development/testing.")
        self.stdout.write("Change this password before using the system in production.")
