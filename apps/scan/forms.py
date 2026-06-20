from django import forms

from apps.assets.forms import ASSET_FIELD_ORDER
from apps.assets.models import Asset
from apps.assets.site_names import apply_site_name_fields, resolve_site_name


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
            "site_name",
            "asset_number",
            "product_name",
            "serial_number",
            "model_number",
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
        apply_site_name_fields(
            self,
            self.known_site_names,
            default_site_name=default_site_name,
        )
        self.fields["barcode_value"].required = False
        self.fields["asset_number"].required = False
        self.fields["asset_number"].help_text = "Leave blank to auto-assign the next number."
        self.order_fields(ASSET_FIELD_ORDER)

    def clean(self):
        cleaned_data = super().clean()
        resolve_site_name(cleaned_data, default_site_name=self.default_site_name, errors_form=self)
        return cleaned_data

    def clean_asset_number(self):
        value = self.cleaned_data.get("asset_number")
        return value or None
