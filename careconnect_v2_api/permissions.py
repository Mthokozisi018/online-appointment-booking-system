from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import GreenChoiceStaffProfile, UserRole


def get_role(user):
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser or user.is_staff:
        return UserRole.Role.ADMIN
    role = getattr(user, "v2_role", None)
    return role.role if role else None


def get_greenchoice_role(user):
    if not user or not user.is_authenticated or not user.is_active:
        return None
    profile = getattr(user, "greenchoice_staff_profile", None)
    return profile.role if profile else None


class IsGreenChoiceStaff(BasePermission):
    message = "GreenChoice staff access is required."

    def has_permission(self, request, view):
        return get_greenchoice_role(request.user) in {
            GreenChoiceStaffProfile.Role.MANAGER,
            GreenChoiceStaffProfile.Role.RECEPTIONIST,
        }


class IsGreenChoiceManager(BasePermission):
    message = "GreenChoice manager access is required."

    def has_permission(self, request, view):
        return get_greenchoice_role(request.user) == GreenChoiceStaffProfile.Role.MANAGER


class IsGreenChoiceReceptionist(BasePermission):
    message = "GreenChoice receptionist access is required."

    def has_permission(self, request, view):
        return get_greenchoice_role(request.user) == GreenChoiceStaffProfile.Role.RECEPTIONIST


class IsPatient(BasePermission):
    message = "Patient access is required."

    def has_permission(self, request, view):
        return get_role(request.user) == UserRole.Role.PATIENT


class IsDoctor(BasePermission):
    message = "Doctor access is required."

    def has_permission(self, request, view):
        return get_role(request.user) == UserRole.Role.DOCTOR


class IsAdminRole(BasePermission):
    message = "Administrator access is required."

    def has_permission(self, request, view):
        return get_role(request.user) == UserRole.Role.ADMIN


class IsOwnerPatientOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        role = get_role(request.user)
        if role == UserRole.Role.ADMIN:
            return True
        if getattr(obj, "patient_id", None) == request.user.id:
            return True
        if request.method in SAFE_METHODS and role == UserRole.Role.DOCTOR:
            doctor_profile = getattr(request.user, "v2_doctor_profile", None)
            return bool(doctor_profile and getattr(obj, "doctor_id", None) == doctor_profile.id)
        return False
