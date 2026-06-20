from django import forms

from apps.assets.models import Asset

NEW_SITE_VALUE = "__new__"


def get_known_site_names(request=None):
    names = set(
        Asset.objects.exclude(site_name="")
        .values_list("site_name", flat=True)
        .distinct()
    )
    if request is not None:
        for meta in request.session.get("scan_sessions_meta", {}).values():
            site = (meta.get("site_name") or "").strip()
            if site:
                names.add(site)
    return sorted(names, key=str.lower)


def get_site_names_with_assets(include_archived=False):
    qs = Asset.objects.exclude(site_name="")
    if not include_archived:
        qs = qs.filter(is_archived=False)
    return sorted(set(qs.values_list("site_name", flat=True)), key=str.lower)


def apply_site_name_fields(form, known_site_names, *, default_site_name="", current_site_name=""):
    if form.instance.pk:
        current = (current_site_name or form.instance.site_name or "").strip()
    else:
        current = (current_site_name or default_site_name or form.initial.get("site_name") or "").strip()

    names = list(known_site_names or [])
    if current and current not in names:
        names.append(current)
    names = sorted(set(names), key=str.lower)

    choices = [("", "Select a site…")]
    choices.extend((name, name) for name in names)
    choices.append((NEW_SITE_VALUE, "+ Add new site…"))

    form.fields["site_name"] = forms.ChoiceField(
        choices=choices,
        required=False,
        label="Site name",
        widget=forms.Select(attrs={"class": "form-input site-name-select"}),
        help_text="Choose which site this asset belongs to.",
    )
    form.fields["new_site_name"] = forms.CharField(
        required=False,
        label="New site name",
        widget=forms.TextInput(
            attrs={
                "class": "form-input new-site-name-input",
                "placeholder": "Enter a new site name",
            }
        ),
    )

    if current and any(value == current for value, _ in choices):
        form.fields["site_name"].initial = current
    elif current:
        form.fields["site_name"].initial = NEW_SITE_VALUE
        form.fields["new_site_name"].initial = current


def resolve_site_name(cleaned_data, *, default_site_name="", errors_form=None):
    site = cleaned_data.get("site_name", "")
    if site == NEW_SITE_VALUE:
        site = (cleaned_data.get("new_site_name") or "").strip()
    elif site:
        site = site.strip()
    elif default_site_name:
        site = default_site_name.strip()

    if not site and errors_form is not None:
        errors_form.add_error("site_name", "Please select or enter a site name.")

    cleaned_data["site_name"] = site
    return site
