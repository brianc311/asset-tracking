from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.admin_site import recaptcha_admin_site
from apps.accounts.models import User


@admin.register(User, site=recaptcha_admin_site)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Asset Tracking", {"fields": ("role", "theme_preference")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Asset Tracking", {"fields": ("role", "theme_preference")}),
    )
