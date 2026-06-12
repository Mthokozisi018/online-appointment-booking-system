from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from careconnect_v2_api.models import (
    Clinic,
    DoctorAvailability,
    DoctorClinic,
    DoctorLanguage,
    DoctorProfile,
    Review,
    Specialty,
    TimeSlot,
    UserRole,
)


SPECIALTIES = [
    ("General", "stethoscope", "blue"),
    ("Dentist", "tooth", "green"),
    ("Dermatologist", "face", "purple"),
    ("Pediatrician", "baby", "orange"),
]

DOCTORS = [
    {
        "email": "sipho.dlamini@careconnect.test",
        "first_name": "Sipho",
        "last_name": "Dlamini",
        "specialty": "General",
        "label": "General Practitioner",
        "qualification": "MBChB, MMed (Family Medicine)",
        "fee": 350,
        "rating": "4.8",
        "reviews": 128,
        "distance": "1.2 km",
        "image": "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?auto=format&fit=crop&w=240&q=80",
        "slots": ["09:00", "10:30", "12:00", "15:30"],
        "languages": [("EN", "English"), ("ZU", "Zulu"), ("XH", "Xhosa")],
    },
    {
        "email": "lerato.mokoena@careconnect.test",
        "first_name": "Lerato",
        "last_name": "Mokoena",
        "specialty": "Dermatologist",
        "label": "Dermatologist",
        "qualification": "FC Derm SA",
        "fee": 500,
        "rating": "4.9",
        "reviews": 96,
        "distance": "2.4 km",
        "image": "https://images.unsplash.com/photo-1594824476967-48c8b964273f?auto=format&fit=crop&w=240&q=80",
        "slots": ["09:30", "11:00", "14:00", "16:30"],
        "languages": [("EN", "English"), ("ZU", "Zulu")],
    },
    {
        "email": "ahmed.khan@careconnect.test",
        "first_name": "Ahmed",
        "last_name": "Khan",
        "specialty": "Dentist",
        "label": "Dentist",
        "qualification": "BDS",
        "fee": 450,
        "rating": "4.7",
        "reviews": 87,
        "distance": "2.7 km",
        "image": "https://images.unsplash.com/photo-1537368910025-700350fe46c7?auto=format&fit=crop&w=240&q=80",
        "slots": ["08:30", "10:00", "13:00", "15:00"],
        "languages": [("EN", "English"), ("AF", "Afrikaans")],
    },
]


class Command(BaseCommand):
    help = "Seed CareConnect V2 demo doctors, clinics, availability, and slots."

    def handle(self, *args, **options):
        specialties = {}
        for name, icon, tone in SPECIALTIES:
            specialties[name], _ = Specialty.objects.update_or_create(
                slug=slugify(name),
                defaults={"name": name, "icon": icon, "tone": tone},
            )

        clinic, _ = Clinic.objects.update_or_create(
            name="HealthLife Medical Centre",
            defaults={
                "address": "123 Durban Road, Glenwood, Durban, 4001",
                "city": "Durban",
                "suburb": "Glenwood",
                "province": "KwaZulu-Natal",
                "latitude": "-29.858680",
                "longitude": "31.021840",
            },
        )

        for item in DOCTORS:
            user, _ = User.objects.update_or_create(
                username=item["email"],
                defaults={"email": item["email"], "first_name": item["first_name"], "last_name": item["last_name"]},
            )
            user.set_password("CareConnectV2!123")
            user.save()
            UserRole.objects.update_or_create(user=user, defaults={"role": UserRole.Role.DOCTOR})
            doctor, _ = DoctorProfile.objects.update_or_create(
                user=user,
                defaults={
                    "specialty": specialties[item["specialty"]],
                    "qualification": item["qualification"],
                    "about": f"Dr. {item['last_name']} provides trusted, patient-first healthcare with a calm modern CareConnect experience.",
                    "image_url": item["image"],
                    "consultation_fee": item["fee"],
                    "rating": item["rating"],
                    "review_count": item["reviews"],
                    "experience_years": 8,
                    "verified": True,
                },
            )
            DoctorClinic.objects.update_or_create(
                doctor=doctor,
                clinic=clinic,
                defaults={"is_primary": True, "distance_label": item["distance"]},
            )
            for code, language_name in item["languages"]:
                DoctorLanguage.objects.update_or_create(doctor=doctor, code=code, defaults={"name": language_name})
            DoctorAvailability.objects.update_or_create(
                doctor=doctor,
                day=DoctorAvailability.Day.MONDAY,
                defaults={"start_time": "08:30", "end_time": "17:30", "slot_duration_minutes": 30, "is_active": True},
            )
            Review.objects.update_or_create(
                doctor=doctor,
                patient_name="Thando M.",
                defaults={"rating": 5, "comment": "Professional, kind, and easy to book."},
            )
            for slot_time in item["slots"]:
                start = datetime.strptime(slot_time, "%H:%M").time()
                end = (datetime.combine(timezone.localdate(), start) + timedelta(minutes=30)).time()
                for day_offset in range(1, 15):
                    TimeSlot.objects.update_or_create(
                        doctor=doctor,
                        clinic=clinic,
                        date=timezone.localdate() + timedelta(days=day_offset),
                        start_time=start,
                        defaults={"end_time": end, "status": TimeSlot.Status.OPEN},
                    )

        self.stdout.write(self.style.SUCCESS("CareConnect V2 seed data created."))
