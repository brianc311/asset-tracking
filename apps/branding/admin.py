from django.contrib import admin

from apps.accounts.admin_site import recaptcha_admin_site
from apps.branding.models import SiteBranding


@admin.register(SiteBranding, site=recaptcha_admin_site)
class SiteBrandingAdmin(admin.ModelAdmin):
    list_display = ("site_name", "updated_at")

    def has_add_permission(self, request):
        return not SiteBranding.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
