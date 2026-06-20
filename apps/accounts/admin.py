from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.admin_site import recaptcha_admin_site
from apps.accounts.models import AccessLog, BlockedIP, User


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


@admin.register(AccessLog, site=recaptcha_admin_site)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "ip_address", "event_type", "path", "username")
    list_filter = ("event_type",)
    search_fields = ("ip_address", "path", "username")
    readonly_fields = ("created_at", "ip_address", "event_type", "path", "username", "user_agent")


@admin.register(BlockedIP, site=recaptcha_admin_site)
class BlockedIPAdmin(admin.ModelAdmin):
    list_display = ("ip_address", "is_active", "reason", "blocked_by", "created_at")
    list_filter = ("is_active",)
    search_fields = ("ip_address", "reason")
