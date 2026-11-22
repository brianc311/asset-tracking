LABEL_FIELD_KEYS = ("serial", "mac", "mac_2", "model", "location", "barcode")
DEFAULT_LABEL_FIELDS = ("serial", "mac", "mac_2")
LABEL_FIELD_LABELS = {
    "serial": "Serial",
    "mac": "MAC",
    "mac_2": "MAC 2",
    "model": "Model",
    "location": "Location",
    "barcode": "Barcode",
}


def parse_label_fields(raw: str | None) -> tuple[str, ...]:
    if raw is None:
        return DEFAULT_LABEL_FIELDS
    allowed = set(LABEL_FIELD_KEYS)
    seen = []
    for part in raw.split(","):
        key = part.strip()
        if key in allowed and key not in seen:
            seen.append(key)
    return tuple(key for key in LABEL_FIELD_KEYS if key in seen)


def device_label_main_value(asset) -> str:
    device_name = (asset.device_name or "").strip()
    if device_name:
        return device_name
    return (asset.serial_number or "").strip()


def label_field_value(asset, key: str) -> str:
    values = {
        "serial": asset.serial_number,
        "mac": asset.mac_address,
        "mac_2": asset.mac_address_2,
        "model": asset.model_number,
        "location": asset.location,
        "barcode": asset.barcode_value,
    }
    return (values.get(key) or "").strip()


def device_label_extra_lines(asset, field_keys) -> list[str]:
    main = device_label_main_value(asset)
    lines = []
    for key in field_keys:
        value = label_field_value(asset, key)
        if not value:
            continue
        if key == "serial" and value == main:
            continue
        lines.append(f"{LABEL_FIELD_LABELS[key]}: {value}")
    return lines
