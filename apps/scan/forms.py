from django import forms

from apps.assets.forms import ASSET_FIELD_ORDER
from apps.assets.mac import MAC_ERROR, normalize_mac
from apps.assets.models import Asset
from apps.assets.product_types import apply_product_type_fields, resolve_product_name
from apps.assets.site_names import apply_site_name_choices, apply_site_name_fields, resolve_site_name


class StartScanForm(forms.Form):
    def __init__(self, *args, known_site_names=None, default_site_name="", **kwargs):
        super().__init__(*args, **kwargs)
        apply_site_name_choices(self, known_site_names, default_site_name=default_site_name)
        self.fields["site_name"].help_text = (
            "Choose the site you are scanning. Items and reports will be grouped under this name."
        )

    def clean(self):
        cleaned_data = super().clean()
        resolve_site_name(cleaned_data, errors_form=self)
        return cleaned_data


class StartBatchForm(forms.Form):
    def __init__(
        self,
        *args,
        known_site_names=None,
        known_product_names=None,
        default_site_name="",
        default_product_name="",
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        apply_site_name_choices(self, known_site_names, default_site_name=default_site_name)
        apply_product_type_fields(self, known_product_names, default_product_name=default_product_name)
        self.fields["site_name"].help_text = "Site for this batch."
        self.fields["product_name"].help_text = "Scan all of this type, then change type for the next batch."

    def clean(self):
        cleaned_data = super().clean()
        resolve_site_name(cleaned_data, errors_form=self)
        resolve_product_name(cleaned_data, errors_form=self)
        return cleaned_data


class BatchItemForm(forms.Form):
    serial_number = forms.CharField(
        max_length=128,
        widget=forms.TextInput(
            attrs={"class": "form-input", "id": "id_serial_number", "placeholder": "Serial number"}
        ),
    )
    mac_address = forms.CharField(
        max_length=17,
        widget=forms.TextInput(
            attrs={"class": "form-input", "id": "id_mac_address", "placeholder": "MAC address"}
        ),
    )
    mac_address_2 = forms.CharField(
        required=False,
        max_length=17,
        widget=forms.TextInput(
            attrs={"class": "form-input", "id": "id_mac_address_2", "placeholder": "Second MAC"}
        ),
    )
    skip_mac_2 = forms.BooleanField(required=False, label="Skip 2nd MAC")

    def _clean_mac(self, raw):
        try:
            return normalize_mac(raw)
        except ValueError:
            raise forms.ValidationError(MAC_ERROR)

    def clean_mac_address(self):
        return self._clean_mac(self.cleaned_data.get("mac_address", ""))

    def clean_mac_address_2(self):
        raw = self.cleaned_data.get("mac_address_2", "")
        if not raw:
            return ""
        return self._clean_mac(raw)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("skip_mac_2"):
            cleaned["mac_address_2"] = ""
        elif not cleaned.get("mac_address_2"):
            self.add_error("mac_address_2", "Enter the second MAC or check Skip 2nd MAC.")
        return cleaned


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
