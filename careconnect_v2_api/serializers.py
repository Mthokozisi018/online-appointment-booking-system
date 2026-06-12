from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import (
    Appointment,
    Clinic,
    DoctorAvailability,
    DoctorClinic,
    DoctorLanguage,
    DoctorProfile,
    FavoriteDoctor,
    GreenChoiceStaffProfile,
    CustomerRecord,
    InventoryItem,
    Notification,
    PatientProfile,
    Product,
    ProductCategory,
    Promotion,
    Review,
    SaleLineItem,
    SaleTransaction,
    Specialty,
    TimeSlot,
    UserRole,
)


class ApiUserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    fullName = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "fullName", "role"]

    def get_fullName(self, obj):
        return obj.get_full_name() or obj.username

    def get_role(self, obj):
        greenchoice_profile = getattr(obj, "greenchoice_staff_profile", None)
        if greenchoice_profile:
            return greenchoice_profile.role
        if obj.is_staff or obj.is_superuser:
            return UserRole.Role.ADMIN
        return getattr(getattr(obj, "v2_role", None), "role", UserRole.Role.PATIENT)


class RegisterSerializer(serializers.Serializer):
    firstName = serializers.CharField(max_length=150)
    lastName = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=32)
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_password(self, value):
        temp_user = User(username=self.initial_data.get("email", ""), email=self.initial_data.get("email", ""))
        password_validation.validate_password(value, temp_user)
        return value

    def validate(self, attrs):
        attrs["email"] = attrs["email"].lower().strip()
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["firstName"],
            last_name=validated_data["lastName"],
        )
        UserRole.objects.create(user=user, role=UserRole.Role.PATIENT)
        PatientProfile.objects.create(user=user, phone=validated_data["phone"])
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["email"].lower().strip(),
            password=attrs["password"],
        )
        if not user:
            raise serializers.ValidationError({"non_field_errors": ["Invalid email or password."]})
        attrs["user"] = user
        return attrs


class GreenChoiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ["id", "name", "slug", "description", "icon", "is_active"]


class GreenChoiceProductSerializer(serializers.ModelSerializer):
    categoryName = serializers.CharField(source="category.name", read_only=True)
    categorySlug = serializers.CharField(source="category.slug", read_only=True)
    quantityAvailable = serializers.IntegerField(source="inventory_item.quantity_available", read_only=True, default=0)
    lowStockThreshold = serializers.IntegerField(source="inventory_item.low_stock_threshold", read_only=True, default=0)
    expiryDate = serializers.DateField(source="inventory_item.expiry_date", read_only=True, allow_null=True)
    hasActivePromotion = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "sku",
            "categoryName",
            "categorySlug",
            "subcategory",
            "description",
            "image_url",
            "unit_size",
            "selling_price",
            "is_active",
            "is_archived",
            "is_new",
            "quantityAvailable",
            "lowStockThreshold",
            "expiryDate",
            "hasActivePromotion",
        ]

    def get_hasActivePromotion(self, obj):
        today = timezone.localdate()
        return obj.promotions.filter(is_active=True, start_date__lte=today, end_date__gte=today).exists() or obj.category.promotions.filter(is_active=True, start_date__lte=today, end_date__gte=today).exists()


class GreenChoiceInventoryItemSerializer(serializers.ModelSerializer):
    product = GreenChoiceProductSerializer(read_only=True)

    class Meta:
        model = InventoryItem
        fields = ["id", "product", "quantity_available", "low_stock_threshold", "expiry_date", "batch_number", "updated_at"]


class GreenChoiceCustomerRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerRecord
        fields = ["id", "first_name", "surname", "mobile_number", "email", "location", "notes", "eligibility_verified", "consent_to_store_details", "created_at"]

    def validate(self, attrs):
        email = (attrs.get("email") or "").strip().lower()
        phone = attrs.get("mobile_number", "").strip()
        if email:
            attrs["email"] = email
            if CustomerRecord.objects.filter(email__iexact=email).exists():
                raise serializers.ValidationError({"email": ["A customer record with this email already exists."]})
        if phone and CustomerRecord.objects.filter(mobile_number=phone).exists():
            raise serializers.ValidationError({"mobile_number": ["A customer record with this mobile number already exists."]})
        return attrs

    def create(self, validated_data):
        return CustomerRecord.objects.create(created_by=self.context["request"].user, **validated_data)


class GreenChoiceSaleLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleLineItem
        fields = ["id", "product_name_snapshot", "unit_price_snapshot", "quantity", "line_total"]


class GreenChoiceSaleSerializer(serializers.ModelSerializer):
    receptionistName = serializers.CharField(source="receptionist.get_full_name", read_only=True)
    customerName = serializers.SerializerMethodField()
    items = GreenChoiceSaleLineItemSerializer(source="line_items", many=True, read_only=True)

    class Meta:
        model = SaleTransaction
        fields = ["id", "transaction_number", "receptionistName", "customerName", "subtotal", "discount_total", "tax_total", "total", "payment_status", "sale_status", "created_at", "items"]

    def get_customerName(self, obj):
        return str(obj.customer) if obj.customer else ""


class GreenChoiceStaffSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="greenchoice_staff_profile.role")
    fullName = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "fullName", "role", "is_active", "last_login"]

    def get_fullName(self, obj):
        return obj.get_full_name() or obj.email


class GreenChoicePromotionSerializer(serializers.ModelSerializer):
    categoryName = serializers.CharField(source="category.name", read_only=True)
    productName = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = Promotion
        fields = ["id", "name", "description", "discount_type", "discount_value", "categoryName", "productName", "minimum_cart_total", "start_date", "end_date", "is_active"]


class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = ["id", "name", "slug", "icon", "tone"]


class ClinicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinic
        fields = ["id", "name", "address", "city", "suburb", "province", "latitude", "longitude"]


class DoctorClinicSerializer(serializers.ModelSerializer):
    clinic = ClinicSerializer(read_only=True)

    class Meta:
        model = DoctorClinic
        fields = ["id", "clinic", "is_primary", "distance_label"]


class DoctorLanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorLanguage
        fields = ["id", "code", "name"]


class ReviewSerializer(serializers.ModelSerializer):
    patientName = serializers.CharField(source="patient_name")

    class Meta:
        model = Review
        fields = ["id", "patientName", "rating", "comment"]


class TimeSlotSerializer(serializers.ModelSerializer):
    time = serializers.TimeField(source="start_time", format="%H:%M")
    available = serializers.SerializerMethodField()

    class Meta:
        model = TimeSlot
        fields = ["id", "date", "time", "available"]

    def get_available(self, obj):
        return obj.status == TimeSlot.Status.OPEN


class DoctorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="display_name", read_only=True)
    specialty = serializers.CharField(source="specialty.name", read_only=True)
    specialtyId = serializers.CharField(source="specialty.slug", read_only=True)
    qualification = serializers.CharField()
    image = serializers.URLField(source="image_url")
    fee = serializers.SerializerMethodField()
    consultationFee = serializers.IntegerField(source="consultation_fee")
    reviews_count = serializers.IntegerField(source="review_count", read_only=True)
    reviews = serializers.IntegerField(source="review_count", read_only=True)
    reviewItems = serializers.SerializerMethodField()
    clinic = serializers.SerializerMethodField()
    languages = serializers.SerializerMethodField()
    experienceYears = serializers.IntegerField(source="experience_years")
    slots = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()

    class Meta:
        model = DoctorProfile
        fields = [
            "id",
            "name",
            "specialty",
            "specialtyId",
            "qualification",
            "rating",
            "reviews_count",
            "reviews",
            "reviewItems",
            "distance",
            "fee",
            "consultationFee",
            "image",
            "clinic",
            "languages",
            "experienceYears",
            "about",
            "slots",
            "verified",
        ]

    def get_fee(self, obj):
        return f"R{obj.consultation_fee}"

    def _primary_link(self, obj):
        links = list(getattr(obj, "prefetched_clinic_links", []))
        if not links:
            links = list(obj.clinic_links.select_related("clinic").all())
        return next((link for link in links if link.is_primary), links[0] if links else None)

    def get_clinic(self, obj):
        link = self._primary_link(obj)
        if not link:
            return None
        clinic = link.clinic
        return {
            "id": str(clinic.id),
            "name": clinic.name,
            "address": clinic.address,
            "city": clinic.city,
            "distance": link.distance_label,
        }

    def get_distance(self, obj):
        link = self._primary_link(obj)
        return link.distance_label if link else ""

    def get_languages(self, obj):
        languages = getattr(obj, "prefetched_languages", None)
        if languages is None:
            languages = obj.languages.all()
        return [item.code for item in languages]

    def get_reviewItems(self, obj):
        reviews = obj.reviews.filter(is_approved=True)[:5]
        return ReviewSerializer(reviews, many=True).data

    def get_slots(self, obj):
        today = timezone.localdate()
        slots = obj.time_slots.filter(date__gte=today, status=TimeSlot.Status.OPEN).order_by("date", "start_time")[:4]
        return [slot.start_time.strftime("%H:%M") for slot in slots]


class PatientProfileSerializer(serializers.ModelSerializer):
    firstName = serializers.CharField(source="user.first_name", required=False)
    lastName = serializers.CharField(source="user.last_name", required=False)
    email = serializers.EmailField(source="user.email", required=False)
    phone = serializers.CharField()
    dateOfBirth = serializers.DateField(source="date_of_birth", required=False, allow_null=True)
    medicalAidProvider = serializers.CharField(source="medical_aid_provider", required=False, allow_blank=True)
    medicalAidNumber = serializers.CharField(source="medical_aid_number", required=False, allow_blank=True)
    emergencyContactName = serializers.CharField(source="emergency_contact_name", required=False, allow_blank=True)
    emergencyContactPhone = serializers.CharField(source="emergency_contact_phone", required=False, allow_blank=True)

    class Meta:
        model = PatientProfile
        fields = [
            "id",
            "firstName",
            "lastName",
            "email",
            "phone",
            "gender",
            "dateOfBirth",
            "medicalAidProvider",
            "medicalAidNumber",
            "emergencyContactName",
            "emergencyContactPhone",
        ]

    def validate_email(self, value):
        value = value.lower().strip()
        if not value:
            return value
        user = self.instance.user if self.instance else None
        queryset = User.objects.filter(email__iexact=value)
        if user:
            queryset = queryset.exclude(pk=user.pk)
        if queryset.exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            for attr, value in user_data.items():
                if attr == "email":
                    value = value.lower().strip()
                setattr(instance.user, attr, value)
            if "email" in user_data:
                instance.user.username = user_data["email"]
            if user_data:
                instance.user.save()
            instance.save()
        return instance


class AppointmentSerializer(serializers.ModelSerializer):
    doctorId = serializers.PrimaryKeyRelatedField(source="doctor", queryset=DoctorProfile.objects.all())
    doctorName = serializers.CharField(source="doctor.display_name", read_only=True)
    specialty = serializers.CharField(source="doctor.specialty.name", read_only=True)
    doctorImage = serializers.URLField(source="doctor.image_url", read_only=True)
    clinicName = serializers.CharField(source="clinic.name", read_only=True)
    location = serializers.SerializerMethodField(read_only=True)
    patientId = serializers.IntegerField(source="patient_id", read_only=True)
    reasonForVisit = serializers.CharField(source="reason_for_visit")
    consultationFee = serializers.IntegerField(source="consultation_fee", required=False)
    reminderStatus = serializers.CharField(read_only=True, default="Not scheduled")
    medicalAidStatus = serializers.CharField(read_only=True, default="Not provided")
    cancellationReason = serializers.CharField(read_only=True, default="")
    rescheduleInfo = serializers.CharField(read_only=True, default="")
    notes = serializers.CharField(read_only=True, default="")
    time = serializers.TimeField(format="%H:%M", input_formats=["%H:%M", "%H:%M:%S"])
    slotId = serializers.PrimaryKeyRelatedField(source="slot", queryset=TimeSlot.objects.all(), write_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "doctorId",
            "doctorName",
            "specialty",
            "doctorImage",
            "clinicName",
            "location",
            "patientId",
            "date",
            "time",
            "status",
            "reasonForVisit",
            "consultationFee",
            "reminderStatus",
            "medicalAidStatus",
            "cancellationReason",
            "rescheduleInfo",
            "notes",
            "slotId",
        ]
        read_only_fields = ["id", "status"]
        validators = []

    def get_location(self, obj):
        if obj.clinic:
            return f"{obj.clinic.address}, {obj.clinic.city}"
        return ""

    def validate(self, attrs):
        request = self.context["request"]
        doctor = attrs["doctor"]
        slot = attrs["slot"]
        date = attrs["date"]
        time = attrs["time"]

        if date < timezone.localdate():
            raise serializers.ValidationError({"date": ["Appointment date cannot be in the past."]})
        if slot.doctor_id != doctor.id:
            raise serializers.ValidationError({"slotId": ["The selected slot does not belong to this doctor."]})
        if slot.date != date or slot.start_time.replace(second=0, microsecond=0) != time.replace(second=0, microsecond=0):
            raise serializers.ValidationError({"slotId": ["The selected slot does not match the requested date and time."]})
        if slot.status != TimeSlot.Status.OPEN:
            raise serializers.ValidationError({"slotId": ["The selected time slot is no longer available."]})
        if Appointment.objects.filter(doctor=doctor, date=date, time=time, status__in=["pending", "confirmed", "completed"]).exists():
            raise serializers.ValidationError({"time": ["This doctor is already booked at the selected time."]})
        if Appointment.objects.filter(patient=request.user, date=date, time=time, status__in=["pending", "confirmed", "completed"]).exists():
            raise serializers.ValidationError({"time": ["You already have an appointment at this time."]})
        attrs["clinic"] = slot.clinic
        attrs["consultation_fee"] = attrs.get("consultation_fee") or doctor.consultation_fee
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        slot_id = validated_data["slot"].id
        with transaction.atomic():
            slot = TimeSlot.objects.select_for_update().select_related("clinic", "doctor").get(pk=slot_id)
            doctor = validated_data["doctor"]
            date = validated_data["date"]
            time = validated_data["time"]
            if slot.status != TimeSlot.Status.OPEN:
                raise serializers.ValidationError({"slotId": ["The selected time slot is no longer available."]})
            if slot.doctor_id != doctor.id:
                raise serializers.ValidationError({"slotId": ["The selected slot does not belong to this doctor."]})
            if slot.date != date or slot.start_time.replace(second=0, microsecond=0) != time.replace(second=0, microsecond=0):
                raise serializers.ValidationError({"slotId": ["The selected slot does not match the requested date and time."]})
            if date < timezone.localdate():
                raise serializers.ValidationError({"date": ["Appointment date cannot be in the past."]})
            if Appointment.objects.filter(doctor=doctor, date=date, time=time, status__in=["pending", "confirmed", "completed"]).exists():
                raise serializers.ValidationError({"time": ["This doctor is already booked at the selected time."]})
            if Appointment.objects.filter(patient=request.user, date=date, time=time, status__in=["pending", "confirmed", "completed"]).exists():
                raise serializers.ValidationError({"time": ["You already have an appointment at this time."]})
            validated_data["slot"] = slot
            validated_data["clinic"] = slot.clinic
            appointment = Appointment.objects.create(patient=request.user, **validated_data)
            slot.status = TimeSlot.Status.BOOKED
            slot.save(update_fields=["status", "updated_at"])
        return appointment


class FavoriteDoctorSerializer(serializers.ModelSerializer):
    doctor = DoctorSerializer(read_only=True)
    doctorId = serializers.PrimaryKeyRelatedField(source="doctor", queryset=DoctorProfile.objects.all(), write_only=True)

    class Meta:
        model = FavoriteDoctor
        fields = ["id", "doctor", "doctorId", "created_at"]

    def validate_doctorId(self, value):
        request = self.context.get("request")
        if request and FavoriteDoctor.objects.filter(patient=request.user, doctor=value).exists():
            raise serializers.ValidationError("This doctor is already in your favorites.")
        return value


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "body", "is_read", "created_at"]


class DoctorAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorAvailability
        fields = ["id", "doctor", "day", "start_time", "end_time", "slot_duration_minutes", "is_active"]
