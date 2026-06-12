from django.contrib import admin

from .models import (
    Appointment,
    Clinic,
    DoctorAvailability,
    DoctorClinic,
    DoctorLanguage,
    DoctorProfile,
    FavoriteDoctor,
    GreenChoiceStaffProfile,
    ProductCategory,
    Product,
    InventoryItem,
    StockMovement,
    CustomerRecord,
    SaleTransaction,
    SaleLineItem,
    Promotion,
    AuditLog,
    Notification,
    PatientProfile,
    Review,
    Specialty,
    TimeSlot,
    UserRole,
)


admin.site.register(UserRole)
admin.site.register(GreenChoiceStaffProfile)
admin.site.register(ProductCategory)
admin.site.register(Product)
admin.site.register(InventoryItem)
admin.site.register(StockMovement)
admin.site.register(CustomerRecord)
admin.site.register(SaleTransaction)
admin.site.register(SaleLineItem)
admin.site.register(Promotion)
admin.site.register(AuditLog)
admin.site.register(PatientProfile)
admin.site.register(DoctorProfile)
admin.site.register(Specialty)
admin.site.register(Clinic)
admin.site.register(DoctorClinic)
admin.site.register(DoctorLanguage)
admin.site.register(DoctorAvailability)
admin.site.register(TimeSlot)
admin.site.register(Appointment)
admin.site.register(Review)
admin.site.register(FavoriteDoctor)
admin.site.register(Notification)
