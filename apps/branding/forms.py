from django import forms

from apps.branding.models import SiteBranding


class BrandingForm(forms.ModelForm):
    class Meta:
        model = SiteBranding
        fields = [
            "site_name",
            "tagline",
            "logo",
            "favicon",
            "header_html",
            "footer_html",
            "primary_color",
            "accent_color",
            "header_bg",
            "footer_bg",
            "login_title",
            "login_subtitle",
            "dashboard_title",
            "assets_page_title",
            "scan_page_title",
            "status_page_title",
            "custom_css",
        ]
        widgets = {
            "site_name": forms.TextInput(attrs={"class": "form-input"}),
            "tagline": forms.TextInput(attrs={"class": "form-input"}),
            "header_html": forms.Textarea(attrs={"class": "form-input", "rows": 4}),
            "footer_html": forms.Textarea(attrs={"class": "form-input", "rows": 4}),
            "primary_color": forms.TextInput(attrs={"class": "form-input", "type": "color"}),
            "accent_color": forms.TextInput(attrs={"class": "form-input", "type": "color"}),
            "header_bg": forms.TextInput(attrs={"class": "form-input", "type": "color"}),
            "footer_bg": forms.TextInput(attrs={"class": "form-input", "type": "color"}),
            "login_title": forms.TextInput(attrs={"class": "form-input"}),
            "login_subtitle": forms.TextInput(attrs={"class": "form-input"}),
            "dashboard_title": forms.TextInput(attrs={"class": "form-input"}),
            "assets_page_title": forms.TextInput(attrs={"class": "form-input"}),
            "scan_page_title": forms.TextInput(attrs={"class": "form-input"}),
            "status_page_title": forms.TextInput(attrs={"class": "form-input"}),
            "custom_css": forms.Textarea(attrs={"class": "form-input", "rows": 6}),
        }
