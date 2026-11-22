from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.assets.product_types import resolve_product_name
from apps.assets.site_names import resolve_site_name

BULK_UPDATE_FIELD_CHOICES = (
    ("device_name", "Device Name"),
    ("location", "Location"),
    ("product_name", "Product"),
    ("site_name", "Site"),
    ("model_number", "Model"),
    ("comments", "Comments"),
)
BULK_UPDATE_TEXT_FIELDS = frozenset({"device_name", "location", "model_number"})
BULK_UPDATE_FIELDS = tuple(key for key, _label in BULK_UPDATE_FIELD_CHOICES)
BULK_UPDATE_LABELS = dict(BULK_UPDATE_FIELD_CHOICES)


def resolve_bulk_value(field: str, cleaned_data: dict) -> str:
    if field == "product_name":
        name = resolve_product_name(cleaned_data)
        if not name:
            raise ValidationError("Please select or enter a device type.")
        return name
    if field == "site_name":
        site = resolve_site_name(cleaned_data)
        if not site:
            raise ValidationError("Please select or enter a site name.")
        return site
    if field in BULK_UPDATE_TEXT_FIELDS:
        return (cleaned_data.get("value") or "").strip()
    if field == "comments":
        return cleaned_data.get("comments") or ""
    raise ValidationError("Choose a field to update.")


def apply_bulk_field_update(queryset, *, field: str, value: str, user) -> int:
    if field not in BULK_UPDATE_FIELDS:
        raise ValidationError("Choose a field to update.")
    return queryset.update(
        **{
            field: value,
            "updated_by": user,
            "updated_at": timezone.now(),
        }
    )
