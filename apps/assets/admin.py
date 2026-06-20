from django.contrib import admin
from django.utils import timezone

from apps.accounts.admin_site import recaptcha_admin_site
from apps.assets.models import Asset


@admin.register(Asset, site=recaptcha_admin_site)
class AssetAdmin(admin.ModelAdmin):
    list_display = (
        "product_name",
        "barcode_value",
        "serial_number",
        "model_number",
        "is_archived",
        "created_at",
    )
    list_filter = ("is_archived", "barcode_type", "created_at")
    search_fields = ("product_name", "barcode_value", "serial_number", "model_number")
    readonly_fields = ("uuid", "created_at", "updated_at", "archived_at")

    actions = ["archive_selected", "unarchive_selected"]

    @admin.action(description="Archive selected assets")
    def archive_selected(self, request, queryset):
        queryset.update(is_archived=True, archived_at=timezone.now())

    @admin.action(description="Unarchive selected assets")
    def unarchive_selected(self, request, queryset):
        queryset.update(is_archived=False, archived_at=None)
