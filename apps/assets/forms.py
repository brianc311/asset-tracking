from django import forms

from apps.assets.models import Asset
from apps.assets.site_names import apply_site_name_fields, resolve_site_name

ASSET_FIELD_ORDER = [
    "site_name",
    "new_site_name",
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


class AssetForm(forms.ModelForm):
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
            "product_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Product name"}),
            "serial_number": forms.TextInput(attrs={"class": "form-input", "placeholder": "Serial number"}),
            "model_number": forms.TextInput(attrs={"class": "form-input", "placeholder": "Model number"}),
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


class BulkActionForm(forms.Form):
    ACTION_ARCHIVE = "archive"
    ACTION_DELETE = "delete"
    ACTION_CHOICES = [
        (ACTION_ARCHIVE, "Archive selected"),
        (ACTION_DELETE, "Delete selected"),
    ]
    action = forms.ChoiceField(choices=ACTION_CHOICES)
    asset_ids = forms.CharField(widget=forms.HiddenInput())


class SiteReportEmailForm(forms.Form):
    site_name = forms.ChoiceField(
        label="Site",
        widget=forms.Select(attrs={"class": "form-input"}),
        help_text="Choose the site to include in the PDF report.",
    )
    recipient = forms.EmailField(
        label="Send to email",
        widget=forms.EmailInput(attrs={"class": "form-input", "placeholder": "you@gmail.com"}),
        help_text="The report PDF will be attached to this address.",
    )

    def __init__(self, *args, site_names=None, default_site="", default_recipient="", **kwargs):
        super().__init__(*args, **kwargs)
        names = list(site_names or [])
        if not names:
            self.fields["site_name"].choices = [("", "No sites with assets yet")]
            self.fields["site_name"].disabled = True
        else:
            self.fields["site_name"].choices = [("", "Select a site…")] + [(n, n) for n in names]
            if default_site and default_site in names:
                self.fields["site_name"].initial = default_site
        if default_recipient:
            self.fields["recipient"].initial = default_recipient

    def clean_site_name(self):
        value = self.cleaned_data.get("site_name", "")
        if not value:
            raise forms.ValidationError("Select a site for the report.")
        return value
