from django.db import models


class SiteBranding(models.Model):
    """Singleton white-label configuration editable from the admin console."""

    site_name = models.CharField(max_length=120, default="Asset Tracking")
    tagline = models.CharField(max_length=255, blank=True, default="Track every asset. Anywhere.")
    logo = models.ImageField(upload_to="branding/", blank=True, null=True)
    favicon = models.ImageField(upload_to="branding/", blank=True, null=True)

    header_html = models.TextField(
        blank=True,
        help_text="Custom HTML for the main header area.",
    )
    footer_html = models.TextField(
        blank=True,
        help_text="Custom HTML for the footer.",
    )

    primary_color = models.CharField(max_length=7, default="#6366f1")
    accent_color = models.CharField(max_length=7, default="#8b5cf6")
    header_bg = models.CharField(max_length=7, default="#0f172a")
    footer_bg = models.CharField(max_length=7, default="#0f172a")

    login_title = models.CharField(max_length=120, default="Welcome back")
    login_subtitle = models.CharField(max_length=255, default="Sign in to manage your assets")
    dashboard_title = models.CharField(max_length=120, default="Dashboard")
    assets_page_title = models.CharField(max_length=120, default="Assets")
    scan_page_title = models.CharField(max_length=120, default="Scan Assets")
    status_page_title = models.CharField(max_length=120, default="System Status")

    custom_css = models.TextField(blank=True, help_text="Additional CSS injected site-wide.")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Branding"
        verbose_name_plural = "Site Branding"

    def __str__(self):
        return self.site_name

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass
