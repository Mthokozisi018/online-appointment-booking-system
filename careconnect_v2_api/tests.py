from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Appointment, Clinic, DoctorClinic, DoctorProfile, GreenChoiceStaffProfile, InventoryItem, PatientProfile, Product, ProductCategory, Specialty, TimeSlot, UserRole


class CareConnectV2ApiTests(APITestCase):
    def setUp(self):
        self.specialty = Specialty.objects.create(name="General", slug="general", icon="stethoscope", tone="blue")
        self.clinic = Clinic.objects.create(
            name="HealthLife Medical Centre",
            address="123 Durban Road",
            city="Durban",
            suburb="Glenwood",
            province="KwaZulu-Natal",
        )
        self.patient = User.objects.create_user(
            username="patient@example.com",
            email="patient@example.com",
            password="StrongPass123!",
            first_name="Pat",
            last_name="Ient",
        )
        UserRole.objects.update_or_create(user=self.patient, defaults={"role": UserRole.Role.PATIENT})
        PatientProfile.objects.update_or_create(user=self.patient, defaults={"phone": "+27720000000"})

        self.other_patient = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="StrongPass123!",
            first_name="Other",
            last_name="Patient",
        )
        UserRole.objects.update_or_create(user=self.other_patient, defaults={"role": UserRole.Role.PATIENT})
        PatientProfile.objects.update_or_create(user=self.other_patient, defaults={"phone": "+27720000001"})

        self.doctor_user = User.objects.create_user(
            username="doctor@example.com",
            email="doctor@example.com",
            password="StrongPass123!",
            first_name="Doc",
            last_name="Tor",
        )
        UserRole.objects.update_or_create(user=self.doctor_user, defaults={"role": UserRole.Role.DOCTOR})
        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            specialty=self.specialty,
            qualification="MBChB",
            consultation_fee=350,
            rating="4.80",
            review_count=12,
            experience_years=8,
        )
        DoctorClinic.objects.create(doctor=self.doctor, clinic=self.clinic, is_primary=True, distance_label="1.2 km")
        self.slot = TimeSlot.objects.create(
            doctor=self.doctor,
            clinic=self.clinic,
            date=timezone.localdate() + timedelta(days=1),
            start_time="09:00",
            end_time="09:30",
            status=TimeSlot.Status.OPEN,
        )

    def appointment_payload(self, slot=None):
        slot = slot or self.slot
        return {
            "doctorId": self.doctor.id,
            "slotId": slot.id,
            "date": str(slot.date),
            "time": str(slot.start_time)[:5],
            "reasonForVisit": "Annual checkup",
        }

    def test_auth_register_login_and_me(self):
        response = self.client.post(
            reverse("v2-register"),
            {
                "firstName": "New",
                "lastName": "Patient",
                "email": "new@example.com",
                "phone": "+27720000002",
                "password": "StrongPass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["user"]["role"], UserRole.Role.PATIENT)
        user = User.objects.get(email="new@example.com")
        self.assertEqual(user.v2_role.role, UserRole.Role.PATIENT)
        self.assertTrue(hasattr(user, "v2_patient_profile"))

        self.client.logout()
        response = self.client.post(reverse("v2-login"), {"email": "new@example.com", "password": "StrongPass123!"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(reverse("v2-me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["email"], "new@example.com")

    def test_register_duplicate_email_returns_email_error(self):
        response = self.client.post(
            reverse("v2-register"),
            {
                "firstName": "Pat",
                "lastName": "Ient",
                "email": "patient@example.com",
                "phone": "+27720000002",
                "password": "StrongPass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["message"], "Validation failed")
        self.assertIn("email", response.json()["errors"])

    def test_register_weak_password_returns_password_error(self):
        response = self.client.post(
            reverse("v2-register"),
            {
                "firstName": "Weak",
                "lastName": "Password",
                "email": "weak-password@example.com",
                "phone": "+27720000002",
                "password": "password",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["message"], "Validation failed")
        self.assertIn("password", response.json()["errors"])

    def test_patient_profile_get_and_update_normalizes_email(self):
        self.client.force_authenticate(self.patient)
        response = self.client.get(reverse("v2-patient-profile-current"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.patch(
            reverse("v2-patient-profile-current"),
            {"email": "UPDATED@EXAMPLE.COM", "phone": "+27720000003"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.email, "updated@example.com")

    def test_patient_profile_rejects_duplicate_email(self):
        self.client.force_authenticate(self.patient)
        response = self.client.patch(reverse("v2-patient-profile-current"), {"email": "other@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.json()["errors"])

    def test_doctor_listing(self):
        response = self.client.get(reverse("v2-doctor-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["meta"]["count"], 1)
        self.assertEqual(response.json()["data"][0]["name"], "Doc Tor")

    def test_availability_listing_returns_open_future_slots(self):
        response = self.client.get(reverse("v2-doctor-availability", kwargs={"pk": self.doctor.id}), {"date": str(self.slot.date)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"][0]["time"], "09:00")

    def test_successful_booking_marks_slot_booked(self):
        self.client.force_authenticate(self.patient)
        response = self.client.post(reverse("v2-appointment-list"), self.appointment_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.status, TimeSlot.Status.BOOKED)

    def test_duplicate_booking_is_prevented(self):
        self.client.force_authenticate(self.patient)
        self.client.post(reverse("v2-appointment-list"), self.appointment_payload(), format="json")

        self.client.force_authenticate(self.other_patient)
        response = self.client.post(reverse("v2-appointment-list"), self.appointment_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("slotId", response.json()["errors"])

    def test_booking_requires_patient_role(self):
        self.client.force_authenticate(self.doctor_user)
        response = self.client.post(reverse("v2-appointment-list"), self.appointment_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_booking_requires_authentication(self):
        response = self.client.post(reverse("v2-appointment-list"), self.appointment_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_doctor_can_retrieve_own_appointment(self):
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,
            slot=self.slot,
            date=self.slot.date,
            time=self.slot.start_time,
            reason_for_visit="Annual checkup",
            consultation_fee=350,
        )
        self.client.force_authenticate(self.doctor_user)
        response = self.client.get(reverse("v2-appointment-detail", kwargs={"pk": appointment.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["id"], str(appointment.id))

    def test_cancelling_appointment_reopens_slot(self):
        self.client.force_authenticate(self.patient)
        response = self.client.post(reverse("v2-appointment-list"), self.appointment_payload(), format="json")
        appointment_id = response.json()["data"]["id"]

        response = self.client.post(reverse("v2-appointment-cancel", kwargs={"pk": appointment_id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.slot.refresh_from_db()
        appointment = Appointment.objects.get(pk=appointment_id)
        self.assertEqual(appointment.status, Appointment.Status.CANCELLED)
        self.assertEqual(self.slot.status, TimeSlot.Status.OPEN)

    def test_invalid_query_params_return_400(self):
        response = self.client.get(reverse("v2-doctor-list"), {"max_fee": "not-a-number"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("max_fee", response.json()["errors"])


class GreenChoiceStaffSeedTests(APITestCase):
    def test_seed_greenchoice_staff_is_idempotent_and_uses_hashed_password(self):
        call_command("seed_greenchoice_staff")
        call_command("seed_greenchoice_staff")

        self.assertEqual(User.objects.filter(email="manager@greenchoice.local").count(), 1)
        user = User.objects.get(email="manager@greenchoice.local")
        self.assertEqual(user.get_full_name(), "GreenChoice Manager")
        self.assertTrue(user.is_active)
        self.assertNotEqual(user.password, "ChangeMe123!")
        self.assertTrue(user.check_password("ChangeMe123!"))
        self.assertEqual(user.greenchoice_staff_profile.role, GreenChoiceStaffProfile.Role.MANAGER)

    def test_seeded_manager_can_log_in(self):
        call_command("seed_greenchoice_staff")

        response = self.client.post(
            reverse("v2-login"),
            {"email": "manager@greenchoice.local", "password": "ChangeMe123!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["user"]["role"], GreenChoiceStaffProfile.Role.MANAGER)


class GreenChoiceDashboardPermissionTests(APITestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username="manager@example.com", email="manager@example.com", password="StrongPass123!", first_name="Store", last_name="Manager")
        GreenChoiceStaffProfile.objects.create(user=self.manager, role=GreenChoiceStaffProfile.Role.MANAGER)
        self.receptionist = User.objects.create_user(username="receptionist@example.com", email="receptionist@example.com", password="StrongPass123!", first_name="Store", last_name="Receptionist")
        GreenChoiceStaffProfile.objects.create(user=self.receptionist, role=GreenChoiceStaffProfile.Role.RECEPTIONIST)
        self.category = ProductCategory.objects.create(name="Flower", slug="flower", icon="Leaf")
        self.product = Product.objects.create(name="Gelato 33", sku="TEST-001", category=self.category, subcategory="Indoor", selling_price="185.00", is_active=True)
        InventoryItem.objects.create(product=self.product, quantity_available=12, low_stock_threshold=4)

    def test_manager_can_access_manager_inventory(self):
        self.client.force_authenticate(self.manager)
        response = self.client.get(reverse("greenchoice-manager-inventory"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["totalStockUnits"], 12)

    def test_receptionist_cannot_access_manager_inventory(self):
        self.client.force_authenticate(self.receptionist)
        response = self.client.get(reverse("greenchoice-manager-inventory"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_receptionist_can_browse_products_and_create_customer_record(self):
        self.client.force_authenticate(self.receptionist)
        response = self.client.get(reverse("greenchoice-products"), {"category": "flower"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["meta"]["count"], 1)

        response = self.client.post(
            reverse("greenchoice-customers"),
            {
                "first_name": "Customer",
                "surname": "Record",
                "mobile_number": "+27720000009",
                "email": "customer.record@example.com",
                "eligibility_verified": True,
                "consent_to_store_details": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
