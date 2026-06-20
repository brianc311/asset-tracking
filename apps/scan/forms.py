from django import forms
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox

from apps.assets.models import Asset


class ScanLoginForm(forms.Form):
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox)


class ScanAssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
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
            "location": forms.TextInput(attrs={"class": "form-input", "placeholder": "Location"}),
            "comments": forms.Textarea(attrs={"class": "form-input", "rows": 2, "placeholder": "Comments"}),
            "barcode_type": forms.Select(attrs={"class": "form-input"}),
            "barcode_value": forms.TextInput(attrs={"class": "form-input", "placeholder": "Scan or leave blank to auto-generate"}),
            "photo": forms.FileInput(attrs={"class": "photo-file-input", "accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["barcode_value"].required = False
        self.fields["asset_number"].required = False
        self.fields["asset_number"].help_text = "Leave blank to auto-assign the next number."

    def clean_asset_number(self):
        value = self.cleaned_data.get("asset_number")
        return value or None
