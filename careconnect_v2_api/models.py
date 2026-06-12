import uuid

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.utils import timezone


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class UserRole(TimestampedModel):
    class Role(models.TextChoices):
        PATIENT = "PATIENT", "Patient"
        DOCTOR = "DOCTOR", "Doctor"
        ADMIN = "ADMIN", "Admin"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="v2_role")
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.PATIENT, db_index=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class GreenChoiceStaffProfile(TimestampedModel):
    class Role(models.TextChoices):
        MANAGER = "MANAGER", "Manager"
        RECEPTIONIST = "RECEPTIONIST", "Receptionist"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="greenchoice_staff_profile")
    role = models.CharField(max_length=16, choices=Role.choices, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["role"], name="greenchoice_staff_role_idx")]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.role})"


class ProductCategory(TimestampedModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=60, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(TimestampedModel):
    name = models.CharField(max_length=180)
    sku = models.CharField(max_length=80, unique=True)
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT, related_name="greenchoice_products")
    subcategory = models.CharField(max_length=120, blank=True, db_index=True)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    unit_size = models.CharField(max_length=80, blank=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    is_new = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["category", "is_active", "is_archived"], name="greenchoice_product_active_idx")]

    def __str__(self):
        return f"{self.name} ({self.sku})"


class InventoryItem(TimestampedModel):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="inventory_item")
    quantity_available = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    expiry_date = models.DateField(null=True, blank=True)
    batch_number = models.CharField(max_length=80, blank=True)

    def __str__(self):
        return f"{self.product.name}: {self.quantity_available}"


class CustomerRecord(TimestampedModel):
    first_name = models.CharField(max_length=120)
    surname = models.CharField(max_length=120)
    mobile_number = models.CharField(max_length=32, db_index=True)
    email = models.EmailField(blank=True, db_index=True)
    location = models.CharField(max_length=180, blank=True)
    notes = models.TextField(blank=True)
    eligibility_verified = models.BooleanField(default=False)
    consent_to_store_details = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="greenchoice_customer_records")

    class Meta:
        ordering = ["surname", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.surname}"


class SaleTransaction(TimestampedModel):
    class PaymentStatus(models.TextChoices):
        PENDING_PAYMENT = "PENDING_PAYMENT", "Pending payment"
        PAID = "PAID", "Paid"

    class SaleStatus(models.TextChoices):
        PENDING_PAYMENT = "PENDING_PAYMENT", "Pending payment"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"
        REFUNDED = "REFUNDED", "Refunded"

    transaction_number = models.CharField(max_length=40, unique=True)
    customer = models.ForeignKey(CustomerRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name="sales")
    receptionist = models.ForeignKey(User, on_delete=models.PROTECT, related_name="greenchoice_sales")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=24, choices=PaymentStatus.choices, default=PaymentStatus.PENDING_PAYMENT, db_index=True)
    sale_status = models.CharField(max_length=24, choices=SaleStatus.choices, default=SaleStatus.PENDING_PAYMENT, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.transaction_number


class SaleLineItem(models.Model):
    sale = models.ForeignKey(SaleTransaction, on_delete=models.CASCADE, related_name="line_items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="sale_line_items")
    product_name_snapshot = models.CharField(max_length=180)
    unit_price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product_name_snapshot} x {self.quantity}"


class StockMovement(TimestampedModel):
    class MovementType(models.TextChoices):
        STOCK_IN = "STOCK_IN", "Stock in"
        STOCK_OUT = "STOCK_OUT", "Stock out"
        SALE = "SALE", "Sale"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"
        RETURN = "RETURN", "Return"
        WASTE = "WASTE", "Waste"

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stock_movements")
    movement_type = models.CharField(max_length=20, choices=MovementType.choices, db_index=True)
    quantity = models.IntegerField()
    reason = models.CharField(max_length=255, blank=True)
    staff_user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="greenchoice_stock_movements")
    sale = models.ForeignKey(SaleTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name="stock_movements")


class Promotion(TimestampedModel):
    class DiscountType(models.TextChoices):
        PERCENTAGE = "PERCENTAGE", "Percentage"
        FIXED_AMOUNT = "FIXED_AMOUNT", "Fixed amount"

    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT, null=True, blank=True, related_name="promotions")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, null=True, blank=True, related_name="promotions")
    minimum_cart_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="greenchoice_promotions")

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.discount_value < 0:
            raise ValidationError("Discount cannot be negative.")
        if self.discount_type == self.DiscountType.PERCENTAGE and self.discount_value > 100:
            raise ValidationError("Percentage discount must be between 0 and 100.")
        if self.end_date < self.start_date:
            raise ValidationError("End date cannot be before start date.")


class AuditLog(TimestampedModel):
    staff_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="greenchoice_audit_logs")
    action = models.CharField(max_length=120, db_index=True)
    entity_type = models.CharField(max_length=80, db_index=True)
    entity_id = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]


class PatientProfile(TimestampedModel):
    class Gender(models.TextChoices):
        FEMALE = "female", "Female"
        MALE = "male", "Male"
        NON_BINARY = "non_binary", "Non-binary"
        PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="v2_patient_profile")
    phone = models.CharField(max_length=32, blank=True, db_index=True)
    gender = models.CharField(max_length=32, choices=Gender.choices, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    medical_aid_provider = models.CharField(max_length=120, blank=True)
    medical_aid_number = models.CharField(max_length=80, blank=True)
    emergency_contact_name = models.CharField(max_length=160, blank=True)
    emergency_contact_phone = models.CharField(max_length=32, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Specialty(TimestampedModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=40, blank=True)
    tone = models.CharField(max_length=24, default="blue")

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "specialties"
        indexes = [models.Index(fields=["slug"], name="v2_specialty_slug_idx")]

    def __str__(self):
        return self.name


class Clinic(TimestampedModel):
    name = models.CharField(max_length=180, db_index=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100, db_index=True)
    suburb = models.CharField(max_length=100, blank=True, db_index=True)
    province = models.CharField(max_length=100, blank=True, db_index=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["city", "suburb"], name="v2_clinic_location_idx"),
            models.Index(fields=["latitude", "longitude"], name="v2_clinic_geo_idx"),
        ]

    def __str__(self):
        return self.name


class DoctorProfile(TimestampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="v2_doctor_profile")
    specialty = models.ForeignKey(Specialty, on_delete=models.PROTECT, related_name="doctors")
    qualification = models.CharField(max_length=180, blank=True)
    about = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    consultation_fee = models.PositiveIntegerField(default=0, db_index=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0, db_index=True)
    review_count = models.PositiveIntegerField(default=0)
    experience_years = models.PositiveIntegerField(default=0)
    verified = models.BooleanField(default=True, db_index=True)
    accepts_new_patients = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["user__first_name", "user__last_name"]
        indexes = [
            models.Index(fields=["consultation_fee", "rating"], name="v2_doctor_fee_rating_idx"),
            models.Index(fields=["verified", "accepts_new_patients"], name="v2_doctor_public_idx"),
        ]

    @property
    def display_name(self):
        return self.user.get_full_name() or self.user.username

    def __str__(self):
        return self.display_name


class DoctorClinic(TimestampedModel):
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="clinic_links")
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="doctor_links")
    is_primary = models.BooleanField(default=False)
    distance_label = models.CharField(max_length=24, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["doctor", "clinic"], name="v2_unique_doctor_clinic"),
            models.UniqueConstraint(fields=["doctor"], condition=Q(is_primary=True), name="v2_unique_primary_clinic"),
        ]

    def __str__(self):
        return f"{self.doctor.display_name} @ {self.clinic.name}"


class DoctorLanguage(TimestampedModel):
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="languages")
    code = models.CharField(max_length=12)
    name = models.CharField(max_length=80)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["doctor", "code"], name="v2_unique_doctor_language")]

    def __str__(self):
        return f"{self.doctor.display_name} - {self.code}"


class DoctorAvailability(TimestampedModel):
    class Day(models.TextChoices):
        MONDAY = "monday", "Monday"
        TUESDAY = "tuesday", "Tuesday"
        WEDNESDAY = "wednesday", "Wednesday"
        THURSDAY = "thursday", "Thursday"
        FRIDAY = "friday", "Friday"
        SATURDAY = "saturday", "Saturday"
        SUNDAY = "sunday", "Sunday"

    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="availability_rules")
    day = models.CharField(max_length=16, choices=Day.choices, db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration_minutes = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["doctor", "day", "is_active"], name="v2_availability_idx")]

    def __str__(self):
        return f"{self.doctor.display_name} {self.day}"


class TimeSlot(TimestampedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        BOOKED = "booked", "Booked"
        BLOCKED = "blocked", "Blocked"

    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="time_slots")
    clinic = models.ForeignKey(Clinic, on_delete=models.PROTECT, related_name="time_slots")
    date = models.DateField(db_index=True)
    start_time = models.TimeField(db_index=True)
    end_time = models.TimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN, db_index=True)

    class Meta:
        ordering = ["date", "start_time"]
        constraints = [models.UniqueConstraint(fields=["doctor", "date", "start_time"], name="v2_unique_doctor_slot")]
        indexes = [models.Index(fields=["doctor", "date", "status"], name="v2_slot_doctor_date_idx")]

    def __str__(self):
        return f"{self.doctor.display_name} {self.date} {self.start_time}"


class Appointment(TimestampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="v2_patient_appointments")
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="appointments")
    clinic = models.ForeignKey(Clinic, on_delete=models.PROTECT, related_name="appointments")
    slot = models.OneToOneField(TimeSlot, on_delete=models.PROTECT, related_name="appointment")
    date = models.DateField(db_index=True)
    time = models.TimeField(db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    reason_for_visit = models.CharField(max_length=255)
    consultation_fee = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["date", "time"]
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "date", "time"],
                condition=Q(status__in=["pending", "confirmed", "completed"]),
                name="v2_unique_active_doctor_appointment",
            )
        ]
        indexes = [
            models.Index(fields=["doctor", "date", "time"], name="v2_appt_doctor_datetime_idx"),
            models.Index(fields=["patient", "date"], name="v2_appt_patient_date_idx"),
        ]

    def __str__(self):
        return f"{self.patient.username} with {self.doctor.display_name}"


class Review(TimestampedModel):
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="reviews")
    patient = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="v2_reviews")
    patient_name = models.CharField(max_length=120)
    rating = models.PositiveSmallIntegerField(default=5)
    comment = models.TextField()
    is_approved = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["doctor", "rating"], name="v2_review_doctor_rating_idx")]
        constraints = [models.CheckConstraint(condition=Q(rating__gte=1, rating__lte=5), name="v2_review_rating_range")]


class FavoriteDoctor(TimestampedModel):
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="v2_favorite_doctors")
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="favorited_by")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["patient", "doctor"], name="v2_unique_favorite_doctor")]


class Notification(TimestampedModel):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="v2_notifications")
    title = models.CharField(max_length=160)
    body = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read", "created_at"], name="v2_notification_lookup_idx")]
