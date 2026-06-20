from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

from apps.accounts.admin_site import recaptcha_admin_site

urlpatterns = [
    path("admin/", recaptcha_admin_site.urls),
    path("", include("apps.accounts.urls")),
    path("assets/", include("apps.assets.urls")),
    path("scan/", include("apps.scan.urls")),
    path("status/", include("apps.statuspage.urls")),
    path("console/", include("apps.branding.urls")),
]

if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += staticfiles_urlpatterns()

admin.site.site_header = "Asset Tracking Administration"
admin.site.site_title = "Asset Tracking Admin"
admin.site.index_title = "System Administration"
