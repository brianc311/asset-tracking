from django import forms

from apps.assets.models import Asset

NEW_PRODUCT_VALUE = "__new__"


def get_known_product_names():
    names = set(
        Asset.objects.exclude(product_name="")
        .values_list("product_name", flat=True)
        .distinct()
    )
    return sorted(names, key=str.lower)


def apply_product_type_fields(form, known_product_names, *, default_product_name=""):
    current = (default_product_name or "").strip()
    names = list(known_product_names or [])
    if current and current not in names:
        names.append(current)
    names = sorted(set(names), key=str.lower)

    choices = [("", "Select a type…")]
    choices.extend((name, name) for name in names)
    choices.append((NEW_PRODUCT_VALUE, "+ Add new type…"))

    form.fields["product_name"] = forms.ChoiceField(
        choices=choices,
        required=False,
        label="Device type",
        widget=forms.Select(attrs={"class": "form-input product-name-select"}),
    )
    form.fields["new_product_name"] = forms.CharField(
        required=False,
        max_length=255,
        label="New device type",
        widget=forms.TextInput(
            attrs={
                "class": "form-input new-product-name-input",
                "placeholder": "e.g. AP, Switch",
            }
        ),
    )
    if current and any(value == current for value, _ in choices):
        form.fields["product_name"].initial = current
    elif current:
        form.fields["product_name"].initial = NEW_PRODUCT_VALUE
        form.fields["new_product_name"].initial = current


def resolve_product_name(cleaned_data, *, default_product_name="", errors_form=None):
    name = cleaned_data.get("product_name", "")
    if name == NEW_PRODUCT_VALUE:
        name = (cleaned_data.get("new_product_name") or "").strip()
    elif name:
        name = name.strip()
    elif default_product_name:
        name = default_product_name.strip()

    if not name and errors_form is not None:
        errors_form.add_error("product_name", "Please select or enter a device type.")

    cleaned_data["product_name"] = name
    return name
