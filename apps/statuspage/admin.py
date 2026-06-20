from django.contrib import admin

from apps.accounts.admin_site import recaptcha_admin_site
from apps.statuspage.models import Incident, SystemComponent


@admin.register(SystemComponent, site=recaptcha_admin_site)
class SystemComponentAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "display_order")
    list_editable = ("status", "display_order")


@admin.register(Incident, site=recaptcha_admin_site)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("title", "severity", "status", "started_at", "is_public")
    list_filter = ("severity", "status", "is_public")
    filter_horizontal = ("affected_components",)
