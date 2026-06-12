from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from careconnect_v2_api.models import GreenChoiceStaffProfile, InventoryItem, Product, ProductCategory, Promotion


RECEPTIONIST_EMAIL = "receptionist@greenchoice.local"
RECEPTIONIST_PASSWORD = "ChangeMe123!"

CATEGORIES = [
    ("Flower", "flower", "Leaf", ["Indoor", "Greenhouse", "Outdoor"]),
    ("Vape Cartridges", "vape-cartridges", "BatteryCharging", ["Cartridges", "Disposable Vapes", "Battery Packs"]),
    ("Edibles", "edibles", "Cookie", ["Gummies", "Chocolates", "Cookies", "Beverages"]),
    ("Concentrates", "concentrates", "Gem", ["Wax", "Shatter", "Live Resin", "Rosin"]),
    ("Pre-Rolls", "pre-rolls", "Cigarette", ["Single Pre-roll", "Multi-pack", "Infused"]),
    ("Beverages", "beverages", "CupSoda", ["Sparkling", "Tea", "Juice"]),
    ("Tinctures & Oils", "tinctures-oils", "Droplet", ["Tinctures", "Oils", "Capsules"]),
    ("Topicals", "topicals", "Hand", ["Balms", "Creams", "Roll-ons"]),
    ("Accessories", "accessories", "ShoppingBag", ["Batteries", "Papers", "Storage"]),
]

PRODUCTS = [
    ("Gelato 33", "GC-FLW-001", "flower", "Indoor", "3.5 g", "185.00", 28, 8, True),
    ("Durban Poison", "GC-FLW-002", "flower", "Outdoor", "3.5 g", "99.00", 7, 8, False),
    ("Lemon Haze Cartridge", "GC-VAP-001", "vape-cartridges", "Cartridges", "1 g", "360.00", 44, 10, False),
    ("Berry Dream Disposable", "GC-VAP-002", "vape-cartridges", "Disposable Vapes", "1 g", "420.00", 0, 6, True),
    ("Balanced Berry Gummies", "GC-EDB-001", "edibles", "Gummies", "10 x 10 mg", "145.00", 60, 12, False),
    ("Midnight Dark Chocolate", "GC-EDB-002", "edibles", "Chocolates", "100 mg", "175.00", 29, 8, False),
    ("Citrus Wax", "GC-CON-001", "concentrates", "Wax", "1 g", "390.00", 19, 5, False),
    ("Mango Live Resin", "GC-CON-002", "concentrates", "Live Resin", "1 g", "480.00", 4, 5, True),
    ("Day Shift Pre-roll Pack", "GC-PRR-001", "pre-rolls", "Multi-pack", "5 x 0.5 g", "210.00", 35, 8, False),
    ("Sparkling Citrus Social", "GC-BEV-001", "beverages", "Sparkling", "5 mg can", "75.00", 80, 15, True),
    ("Calm Tincture", "GC-OIL-001", "tinctures-oils", "Tinctures", "30 ml", "320.00", 32, 6, False),
    ("Mint Recovery Balm", "GC-TOP-001", "topicals", "Balms", "50 ml", "190.00", 3, 5, False),
    ("Palm 510 Battery", "GC-ACC-001", "accessories", "Batteries", "650 mAh", "180.00", 55, 10, False),
]


class Command(BaseCommand):
    help = "Seed GreenChoice MVP dashboard demo data and a receptionist test account."

    def handle(self, *args, **options):
        call_command("seed_greenchoice_staff")
        User = get_user_model()

        with transaction.atomic():
            first_name, last_name = "GreenChoice Receptionist".split(" ", 1)
            receptionist, _ = User.objects.get_or_create(
                username=RECEPTIONIST_EMAIL,
                defaults={"email": RECEPTIONIST_EMAIL, "first_name": first_name, "last_name": last_name, "is_active": True},
            )
            receptionist.email = RECEPTIONIST_EMAIL
            receptionist.first_name = first_name
            receptionist.last_name = last_name
            receptionist.is_active = True
            receptionist.set_password(RECEPTIONIST_PASSWORD)
            receptionist.save(update_fields=["username", "email", "first_name", "last_name", "is_active", "password"])
            GreenChoiceStaffProfile.objects.update_or_create(user=receptionist, defaults={"role": GreenChoiceStaffProfile.Role.RECEPTIONIST})

            categories = {}
            for name, slug, icon, _subcategories in CATEGORIES:
                categories[slug], _ = ProductCategory.objects.update_or_create(
                    slug=slug,
                    defaults={"name": name, "icon": icon, "description": f"{name} inventory category.", "is_active": True},
                )

            manager = User.objects.get(email="manager@greenchoice.local")
            for name, sku, category_slug, subcategory, unit_size, price, quantity, threshold, is_new in PRODUCTS:
                product, _ = Product.objects.update_or_create(
                    sku=sku,
                    defaults={
                        "name": name,
                        "category": categories[category_slug],
                        "subcategory": subcategory,
                        "description": f"{name} product record for GreenChoice inventory browsing.",
                        "unit_size": unit_size,
                        "selling_price": Decimal(price),
                        "is_active": True,
                        "is_archived": False,
                        "is_new": is_new,
                    },
                )
                InventoryItem.objects.update_or_create(
                    product=product,
                    defaults={"quantity_available": quantity, "low_stock_threshold": threshold, "batch_number": f"BATCH-{sku[-3:]}"},
                )

            Promotion.objects.update_or_create(
                name="Opening Week Category Discount",
                defaults={
                    "description": "Development promotion for testing promotion badges.",
                    "discount_type": Promotion.DiscountType.PERCENTAGE,
                    "discount_value": Decimal("10.00"),
                    "category": categories["edibles"],
                    "product": None,
                    "minimum_cart_total": Decimal("0.00"),
                    "start_date": timezone.localdate(),
                    "end_date": timezone.localdate() + timedelta(days=30),
                    "is_active": True,
                    "created_by": manager,
                },
            )

        self.stdout.write(self.style.SUCCESS("GreenChoice demo seed completed."))
        self.stdout.write("")
        self.stdout.write("Development Receptionist Login:")
        self.stdout.write(f"Email: {RECEPTIONIST_EMAIL}")
        self.stdout.write(f"Password: {RECEPTIONIST_PASSWORD}")
        self.stdout.write("Role: RECEPTIONIST")
        self.stdout.write("")
        self.stdout.write("These credentials are only for development/testing.")
