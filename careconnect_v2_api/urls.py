from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("specialties", views.SpecialtyViewSet, basename="v2-specialty")
router.register("clinics", views.ClinicViewSet, basename="v2-clinic")
router.register("doctors", views.DoctorViewSet, basename="v2-doctor")
router.register("appointments", views.AppointmentViewSet, basename="v2-appointment")
router.register("favorites", views.FavoriteDoctorViewSet, basename="v2-favorite")
router.register("reviews", views.ReviewViewSet, basename="v2-review")
router.register("notifications", views.NotificationViewSet, basename="v2-notification")

urlpatterns = [
    path("auth/csrf/", views.csrf_token, name="v2-csrf"),
    path("auth/register/", views.register, name="v2-register"),
    path("auth/login/", views.login_view, name="v2-login"),
    path("auth/logout/", views.logout_view, name="v2-logout"),
    path("auth/me/", views.me, name="v2-me"),
    path("greenchoice/categories/", views.greenchoice_categories, name="greenchoice-categories"),
    path("greenchoice/products/", views.greenchoice_products, name="greenchoice-products"),
    path("greenchoice/manager/summary/", views.greenchoice_manager_summary, name="greenchoice-manager-summary"),
    path("greenchoice/manager/inventory/", views.greenchoice_inventory_summary, name="greenchoice-manager-inventory"),
    path("greenchoice/manager/low-stock/", views.greenchoice_low_stock, name="greenchoice-manager-low-stock"),
    path("greenchoice/manager/sales/", views.greenchoice_sales, name="greenchoice-manager-sales"),
    path("greenchoice/manager/staff/", views.greenchoice_staff, name="greenchoice-manager-staff"),
    path("greenchoice/manager/promotions/", views.greenchoice_promotions, name="greenchoice-manager-promotions"),
    path("greenchoice/customers/", views.greenchoice_customers, name="greenchoice-customers"),
    path("patient/profile/", views.patient_profile, name="v2-patient-profile-current"),
    path("", include(router.urls)),
]
