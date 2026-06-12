from datetime import timedelta

from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .models import (
    Appointment,
    Clinic,
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
    SaleTransaction,
    Specialty,
    TimeSlot,
    UserRole,
)
from .permissions import IsGreenChoiceManager, IsGreenChoiceStaff, IsOwnerPatientOrAdmin, IsPatient, get_role
from .serializers import (
    ApiUserSerializer,
    AppointmentSerializer,
    ClinicSerializer,
    DoctorSerializer,
    FavoriteDoctorSerializer,
    GreenChoiceCategorySerializer,
    GreenChoiceCustomerRecordSerializer,
    GreenChoiceProductSerializer,
    GreenChoicePromotionSerializer,
    GreenChoiceSaleSerializer,
    GreenChoiceStaffSerializer,
    LoginSerializer,
    NotificationSerializer,
    PatientProfileSerializer,
    RegisterSerializer,
    ReviewSerializer,
    SpecialtySerializer,
    TimeSlotSerializer,
)


def api_list(data, count=None):
    return Response({"data": data, "meta": {"count": count if count is not None else len(data), "source": "api"}})


def api_item(data, status_code=status.HTTP_200_OK):
    return Response({"data": data, "meta": {"source": "api"}}, status=status_code)


def doctor_queryset():
    return (
        DoctorProfile.objects.select_related("user", "specialty")
        .prefetch_related(
            Prefetch("clinic_links", queryset=DoctorClinic.objects.select_related("clinic"), to_attr="prefetched_clinic_links"),
            Prefetch("languages", queryset=DoctorLanguage.objects.all(), to_attr="prefetched_languages"),
        )
        .filter(accepts_new_patients=True)
    )


@ensure_csrf_cookie
def csrf_token(request):
    return JsonResponse({"data": {"csrfToken": get_token(request)}, "meta": {"source": "api"}})


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([ScopedRateThrottle])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    login(request, user)
    return api_item({"user": ApiUserSerializer(user).data})


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([ScopedRateThrottle])
def login_view(request):
    serializer = LoginSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data["user"]
    login(request, user)
    return api_item({"user": ApiUserSerializer(user).data})


register.throttle_scope = "register"
login_view.throttle_scope = "login"


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    logout(request)
    return Response({"data": {"message": "Logged out"}, "meta": {"source": "api"}})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def me(request):
    return api_item(ApiUserSerializer(request.user).data)


def active_greenchoice_products():
    return Product.objects.select_related("category", "inventory_item").filter(category__is_active=True, is_active=True, is_archived=False)


def inventory_totals(queryset=None):
    queryset = queryset or active_greenchoice_products()
    items = InventoryItem.objects.select_related("product", "product__category").filter(product__in=queryset)
    total_units = 0
    total_value = 0
    low_stock_count = 0
    out_of_stock_count = 0
    by_category = {}

    for item in items:
        quantity = item.quantity_available
        price = item.product.selling_price
        value = quantity * price
        total_units += quantity
        total_value += value
        if quantity == 0:
            out_of_stock_count += 1
        elif quantity <= item.low_stock_threshold:
            low_stock_count += 1

        category = item.product.category
        bucket = by_category.setdefault(
            category.slug,
            {"id": category.id, "name": category.name, "slug": category.slug, "icon": category.icon, "totalUnits": 0, "estimatedValue": 0},
        )
        bucket["totalUnits"] += quantity
        bucket["estimatedValue"] += value

    for bucket in by_category.values():
        bucket["estimatedValue"] = f"{bucket['estimatedValue']:.2f}"

    return {
        "totalStockUnits": total_units,
        "totalEstimatedStockValue": f"{total_value:.2f}",
        "lowStockCount": low_stock_count,
        "outOfStockCount": out_of_stock_count,
        "categories": list(by_category.values()),
    }


@api_view(["GET"])
@permission_classes([IsGreenChoiceStaff])
def greenchoice_categories(request):
    categories = ProductCategory.objects.filter(is_active=True)
    return api_list(GreenChoiceCategorySerializer(categories, many=True).data, categories.count())


@api_view(["GET"])
@permission_classes([IsGreenChoiceStaff])
def greenchoice_products(request):
    queryset = active_greenchoice_products()
    category = request.query_params.get("category", "").strip()
    search = request.query_params.get("search", "").strip()
    in_stock = request.query_params.get("in_stock", "").lower() in {"1", "true", "yes"}
    on_promotion = request.query_params.get("on_promotion", "").lower() in {"1", "true", "yes"}
    is_new = request.query_params.get("new", "").lower() in {"1", "true", "yes"}

    if category:
        queryset = queryset.filter(category__slug=category)
    if search:
        queryset = queryset.filter(Q(name__icontains=search) | Q(sku__icontains=search) | Q(subcategory__icontains=search))
    if in_stock:
        queryset = queryset.filter(inventory_item__quantity_available__gt=0)
    if is_new:
        queryset = queryset.filter(is_new=True)
    if on_promotion:
        today = timezone.localdate()
        queryset = queryset.filter(Q(promotions__is_active=True, promotions__start_date__lte=today, promotions__end_date__gte=today) | Q(category__promotions__is_active=True, category__promotions__start_date__lte=today, category__promotions__end_date__gte=today)).distinct()

    return api_list(GreenChoiceProductSerializer(queryset, many=True).data, queryset.count())


@api_view(["GET"])
@permission_classes([IsGreenChoiceManager])
def greenchoice_manager_summary(request):
    totals = inventory_totals()
    return api_item({
        **totals,
        "productCount": active_greenchoice_products().count(),
        "staffCount": GreenChoiceStaffProfile.objects.count(),
        "promotionCount": Promotion.objects.filter(is_active=True).count(),
        "salesCount": SaleTransaction.objects.count(),
    })


@api_view(["GET"])
@permission_classes([IsGreenChoiceManager])
def greenchoice_inventory_summary(request):
    return api_item(inventory_totals())


@api_view(["GET"])
@permission_classes([IsGreenChoiceManager])
def greenchoice_low_stock(request):
    items = InventoryItem.objects.select_related("product", "product__category").filter(product__is_active=True, product__is_archived=False)
    status_filter = request.query_params.get("status", "").strip()
    category = request.query_params.get("category", "").strip()
    if category:
        items = items.filter(product__category__slug=category)

    rows = []
    today = timezone.localdate()
    warning_days = 30
    for item in items:
        status_label = None
        if item.quantity_available == 0:
            status_label = "OUT_OF_STOCK"
        elif item.quantity_available <= item.low_stock_threshold:
            status_label = "LOW_STOCK"
        elif item.expiry_date and item.expiry_date <= today + timedelta(days=warning_days):
            status_label = "EXPIRING_SOON"

        if not status_label:
            continue
        if status_filter and status_label != status_filter:
            continue
        rows.append({
            "id": item.id,
            "productName": item.product.name,
            "category": item.product.category.name,
            "quantityAvailable": item.quantity_available,
            "lowStockThreshold": item.low_stock_threshold,
            "estimatedStockValue": f"{item.quantity_available * item.product.selling_price:.2f}",
            "expiryDate": item.expiry_date,
            "lastUpdated": item.updated_at,
            "status": status_label,
        })
    return api_list(rows, len(rows))


@api_view(["GET"])
@permission_classes([IsGreenChoiceManager])
def greenchoice_sales(request):
    sales = SaleTransaction.objects.select_related("receptionist", "customer").prefetch_related("line_items")
    return api_list(GreenChoiceSaleSerializer(sales[:100], many=True).data, sales.count())


@api_view(["GET"])
@permission_classes([IsGreenChoiceManager])
def greenchoice_staff(request):
    users = User.objects.filter(greenchoice_staff_profile__isnull=False).select_related("greenchoice_staff_profile").order_by("email")
    return api_list(GreenChoiceStaffSerializer(users, many=True).data, users.count())


@api_view(["GET"])
@permission_classes([IsGreenChoiceManager])
def greenchoice_promotions(request):
    promotions = Promotion.objects.select_related("category", "product").order_by("-created_at")
    return api_list(GreenChoicePromotionSerializer(promotions, many=True).data, promotions.count())


@api_view(["GET", "POST"])
@permission_classes([IsGreenChoiceStaff])
def greenchoice_customers(request):
    if request.method == "POST":
        serializer = GreenChoiceCustomerRecordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_item(serializer.data, status.HTTP_201_CREATED)

    search = request.query_params.get("search", "").strip()
    customers = CustomerRecord.objects.all()
    if search:
        customers = customers.filter(Q(first_name__icontains=search) | Q(surname__icontains=search) | Q(mobile_number__icontains=search) | Q(email__icontains=search))
    return api_list(GreenChoiceCustomerRecordSerializer(customers[:50], many=True).data, customers.count())


class SpecialtyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Specialty.objects.all()
    serializer_class = SpecialtySerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return api_list(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        return api_item(self.get_serializer(self.get_object()).data)


class ClinicViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Clinic.objects.all()
    serializer_class = ClinicSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        city = request.query_params.get("city")
        suburb = request.query_params.get("suburb")
        if city:
            queryset = queryset.filter(city__icontains=city)
        if suburb:
            queryset = queryset.filter(suburb__icontains=suburb)
        serializer = self.get_serializer(queryset, many=True)
        return api_list(serializer.data, queryset.count())


class DoctorViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DoctorSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = doctor_queryset()
        search = self.request.query_params.get("search", "").strip()
        specialty = self.request.query_params.get("specialty", "").strip()
        max_fee = self.request.query_params.get("max_fee")
        min_rating = self.request.query_params.get("min_rating")
        city = self.request.query_params.get("city", "").strip()
        suburb = self.request.query_params.get("suburb", "").strip()

        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(specialty__name__icontains=search)
                | Q(qualification__icontains=search)
                | Q(clinic_links__clinic__name__icontains=search)
            ).distinct()
        if specialty:
            queryset = queryset.filter(Q(specialty__slug__iexact=specialty) | Q(specialty__name__iexact=specialty))
        if max_fee:
            try:
                max_fee = int(max_fee)
            except (TypeError, ValueError):
                raise ValidationError({"max_fee": ["Enter a valid whole number."]})
            queryset = queryset.filter(consultation_fee__lte=max_fee)
        if min_rating:
            try:
                min_rating = float(min_rating)
            except (TypeError, ValueError):
                raise ValidationError({"min_rating": ["Enter a valid number."]})
            if min_rating < 0 or min_rating > 5:
                raise ValidationError({"min_rating": ["Rating must be between 0 and 5."]})
            queryset = queryset.filter(rating__gte=min_rating)
        if city:
            queryset = queryset.filter(clinic_links__clinic__city__icontains=city).distinct()
        if suburb:
            queryset = queryset.filter(clinic_links__clinic__suburb__icontains=suburb).distinct()
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return api_list(serializer.data, queryset.count())

    def retrieve(self, request, *args, **kwargs):
        return api_item(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=["GET"], url_path="availability")
    def availability(self, request, pk=None):
        doctor = self.get_object()
        date = request.query_params.get("date")
        slots = doctor.time_slots.select_related("clinic").filter(date__gte=timezone.localdate(), status=TimeSlot.Status.OPEN)
        if date:
            slots = slots.filter(date=date)
        serializer = TimeSlotSerializer(slots.order_by("date", "start_time"), many=True)
        return api_list(serializer.data, slots.count())

    @action(detail=True, methods=["GET"], url_path="reviews")
    def reviews(self, request, pk=None):
        reviews = self.get_object().reviews.filter(is_approved=True)
        serializer = ReviewSerializer(reviews, many=True)
        return api_list(serializer.data, reviews.count())


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerPatientOrAdmin]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "booking"
    http_method_names = ["get", "post", "head", "options"]

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsPatient()]
        return super().get_permissions()

    def get_queryset(self):
        role = get_role(self.request.user)
        if role == UserRole.Role.ADMIN:
            return Appointment.objects.select_related("patient", "doctor", "clinic", "slot")
        if role == UserRole.Role.DOCTOR and hasattr(self.request.user, "v2_doctor_profile"):
            return Appointment.objects.filter(doctor=self.request.user.v2_doctor_profile).select_related("patient", "doctor", "clinic", "slot")
        return Appointment.objects.filter(patient=self.request.user).select_related("patient", "doctor", "clinic", "slot")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return api_list(serializer.data, queryset.count())

    def retrieve(self, request, *args, **kwargs):
        return api_item(self.get_serializer(self.get_object()).data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = serializer.save()
        Notification.objects.create(
            recipient=request.user,
            title="Booking request sent",
            body=f"Your appointment with {appointment.doctor.display_name} is pending confirmation.",
        )
        return api_item(self.get_serializer(appointment).data, status.HTTP_201_CREATED)

    @action(detail=True, methods=["POST"], url_path="cancel")
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        if appointment.status in [Appointment.Status.CANCELLED, Appointment.Status.COMPLETED]:
            raise ValidationError({"status": ["This appointment can no longer be cancelled."]})
        with transaction.atomic():
            appointment = Appointment.objects.select_for_update().select_related("slot").get(pk=appointment.pk)
            appointment.status = Appointment.Status.CANCELLED
            appointment.save(update_fields=["status", "updated_at"])
            if appointment.slot_id:
                slot = TimeSlot.objects.select_for_update().get(pk=appointment.slot_id)
                slot.status = TimeSlot.Status.OPEN
                slot.save(update_fields=["status", "updated_at"])
        return api_item(self.get_serializer(appointment).data)


class FavoriteDoctorViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteDoctorSerializer
    permission_classes = [permissions.IsAuthenticated, IsPatient]

    def get_queryset(self):
        return FavoriteDoctor.objects.filter(patient=self.request.user).select_related("doctor", "doctor__user", "doctor__specialty")

    def perform_create(self, serializer):
        serializer.save(patient=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        favorite, _ = FavoriteDoctor.objects.get_or_create(
            patient=request.user,
            doctor=serializer.validated_data["doctor"],
        )
        return api_item(self.get_serializer(favorite).data, status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return api_list(self.get_serializer(queryset, many=True).data, queryset.count())


class PatientProfileViewSet(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = PatientProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsPatient]

    def get_object(self):
        profile, _ = PatientProfile.objects.get_or_create(user=self.request.user)
        return profile

    def list(self, request, *args, **kwargs):
        return api_item(self.get_serializer(self.get_object()).data)

    def retrieve(self, request, *args, **kwargs):
        return api_item(self.get_serializer(self.get_object()).data)

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_item(serializer.data)


@api_view(["GET", "PATCH"])
@permission_classes([permissions.IsAuthenticated, IsPatient])
def patient_profile(request):
    profile, _ = PatientProfile.objects.get_or_create(user=request.user)
    if request.method == "GET":
        return api_item(PatientProfileSerializer(profile).data)
    serializer = PatientProfileSerializer(profile, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return api_item(serializer.data)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return api_list(self.get_serializer(queryset, many=True).data, queryset.count())


class ReviewViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Review.objects.filter(is_approved=True).select_related("doctor", "patient")
    serializer_class = ReviewSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        doctor_id = request.query_params.get("doctor")
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
        return api_list(self.get_serializer(queryset, many=True).data, queryset.count())
