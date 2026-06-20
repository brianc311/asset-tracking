from django import forms

from apps.assets.models import Asset
from apps.assets.site_names import configure_site_name_field


class AssetForm(forms.ModelForm):
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
            "product_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Product name"}),
            "serial_number": forms.TextInput(attrs={"class": "form-input", "placeholder": "Serial number"}),
            "model_number": forms.TextInput(attrs={"class": "form-input", "placeholder": "Model number"}),
            "site_name": forms.TextInput(),
            "location": forms.TextInput(attrs={"class": "form-input", "placeholder": "Room, shelf, or specific spot"}),
            "comments": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Comments"}),
            "barcode_type": forms.Select(attrs={"class": "form-input"}),
            "barcode_value": forms.TextInput(attrs={"class": "form-input", "placeholder": "Leave blank to auto-generate"}),
            "photo": forms.FileInput(attrs={"class": "photo-file-input", "accept": "image/*"}),
        }

    def __init__(self, *args, known_site_names=None, default_site_name="", **kwargs):
        self.known_site_names = known_site_names or []
        self.default_site_name = default_site_name
        super().__init__(*args, **kwargs)
        configure_site_name_field(self.fields["site_name"], self.known_site_names)
        self.fields["site_name"].label = "Site name"
        self.fields["barcode_value"].required = False
        self.fields["asset_number"].required = False
        self.fields["asset_number"].help_text = "Leave blank to auto-assign the next number."
        if not self.instance.pk and default_site_name and not self.initial.get("site_name"):
            self.fields["site_name"].initial = default_site_name

    def clean_site_name(self):
        return (self.cleaned_data.get("site_name") or "").strip()

    def clean_asset_number(self):
        value = self.cleaned_data.get("asset_number")
        return value or None


class BulkActionForm(forms.Form):
    ACTION_ARCHIVE = "archive"
    ACTION_DELETE = "delete"
    ACTION_CHOICES = [
        (ACTION_ARCHIVE, "Archive selected"),
        (ACTION_DELETE, "Delete selected"),
    ]
    action = forms.ChoiceField(choices=ACTION_CHOICES)
    asset_ids = forms.CharField(widget=forms.HiddenInput())
