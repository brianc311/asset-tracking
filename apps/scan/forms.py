from django import forms

from apps.assets.models import Asset
from apps.assets.site_names import configure_site_name_field, get_known_site_names

class StartScanForm(forms.Form):
    site_name = forms.CharField(
        label="Site name",
        max_length=120,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "e.g. Main Office, Warehouse B, 123 Oak St",
                "autofocus": True,
            }
        ),
        help_text="Label this scan session so items and reports stay organized by location.",
    )

    def clean_site_name(self):
        value = (self.cleaned_data.get("site_name") or "").strip()
        if not value:
            raise forms.ValidationError("Enter a site name to start scanning.")
        return value


class ScanAssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            "asset_number",
            "product_name",
            "serial_number",
            "model_number",
            "site_name",
            "location",
            "comments",
            "photo",
            "barcode_type",
            "barcode_value",
        ]
        widgets = {
            "asset_number": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "Leave blank to auto-assign"}
            ),
            "product_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "What is the product?"}),
            "serial_number": forms.TextInput(attrs={"class": "form-input", "placeholder": "Serial number"}),
            "model_number": forms.TextInput(attrs={"class": "form-input", "placeholder": "Model number"}),
            "site_name": forms.TextInput(),
            "location": forms.TextInput(attrs={"class": "form-input", "placeholder": "Room, shelf, or specific spot"}),
            "comments": forms.Textarea(attrs={"class": "form-input", "rows": 2, "placeholder": "Comments"}),
            "barcode_type": forms.Select(attrs={"class": "form-input"}),
            "barcode_value": forms.TextInput(attrs={"class": "form-input", "placeholder": "Scan or leave blank to auto-generate"}),
            "photo": forms.FileInput(attrs={"class": "photo-file-input", "accept": "image/*"}),
        }

    def __init__(self, *args, known_site_names=None, default_site_name="", **kwargs):
        self.default_site_name = default_site_name
        self.known_site_names = known_site_names or []
        super().__init__(*args, **kwargs)
        configure_site_name_field(self.fields["site_name"], self.known_site_names)
        self.fields["site_name"].label = "Site name"
        self.fields["barcode_value"].required = False
        self.fields["asset_number"].required = False
        self.fields["asset_number"].help_text = "Leave blank to auto-assign the next number."
        if default_site_name and not self.initial.get("site_name") and not getattr(self.instance, "site_name", ""):
            self.fields["site_name"].initial = default_site_name

    def clean_site_name(self):
        value = (self.cleaned_data.get("site_name") or "").strip()
        if not value:
            value = (self.default_site_name or "").strip()
        if not value:
            raise forms.ValidationError("Select or enter a site name for this asset.")
        return value
    def clean_asset_number(self):
        value = self.cleaned_data.get("asset_number")
        return value or None
