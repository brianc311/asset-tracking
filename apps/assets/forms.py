from django import forms

from apps.assets.models import Asset

PHOTO_INPUT_ATTRS = {
    "class": "form-input",
    "accept": "image/*",
    "capture": "environment",
}


class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
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
            "product_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Product name"}),
            "serial_number": forms.TextInput(attrs={"class": "form-input", "placeholder": "Serial number"}),
            "model_number": forms.TextInput(attrs={"class": "form-input", "placeholder": "Model number"}),
            "location": forms.TextInput(attrs={"class": "form-input", "placeholder": "Location"}),
            "comments": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Comments"}),
            "barcode_type": forms.Select(attrs={"class": "form-input"}),
            "barcode_value": forms.TextInput(attrs={"class": "form-input", "placeholder": "Leave blank to auto-generate"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["barcode_value"].required = False
        self.fields["photo"].widget.attrs.update(PHOTO_INPUT_ATTRS)
        self.fields["photo"].help_text = "On your phone, tap to take a photo or pick one from your gallery."


class BulkActionForm(forms.Form):
    ACTION_ARCHIVE = "archive"
    ACTION_DELETE = "delete"
    ACTION_CHOICES = [
        (ACTION_ARCHIVE, "Archive selected"),
        (ACTION_DELETE, "Delete selected"),
    ]
    action = forms.ChoiceField(choices=ACTION_CHOICES)
    asset_ids = forms.CharField(widget=forms.HiddenInput())
