REPORT_COLUMN_KEYS = (
    "number",
    "barcode",
    "site",
    "product",
    "device_name",
    "serial",
    "mac",
    "mac_2",
    "model",
    "location",
    "comments",
)

REPORT_COLUMN_LABELS = {
    "number": "#",
    "barcode": "Barcode",
    "site": "Site",
    "product": "Product",
    "device_name": "Device Name",
    "serial": "Serial",
    "mac": "MAC",
    "mac_2": "MAC 2",
    "model": "Model",
    "location": "Location",
    "comments": "Comments",
}


def parse_report_columns(raw: str | None) -> tuple[str, ...]:
    allowed = set(REPORT_COLUMN_KEYS)
    seen = []
    for part in (raw or "").split(","):
        key = part.strip()
        if key in allowed and key not in seen:
            seen.append(key)
    if not seen:
        return REPORT_COLUMN_KEYS
    return tuple(key for key in REPORT_COLUMN_KEYS if key in seen)


def visible_report_columns(column_keys, *, show_mac_2: bool) -> tuple[str, ...]:
    keys = tuple(column_keys or REPORT_COLUMN_KEYS)
    if not show_mac_2:
        keys = tuple(key for key in keys if key != "mac_2")
    return keys


def report_column_cells(asset, *, show_mac_2: bool) -> dict[str, str]:
    comments = asset.comments or "—"
    if asset.comments and len(asset.comments) > 40:
        comments = asset.comments[:40] + "…"
    cells = {
        "number": str(asset.asset_number or "—"),
        "barcode": asset.barcode_value,
        "site": asset.site_name[:20] or "—",
        "product": asset.product_name[:30],
        "device_name": asset.device_name[:40] or "—",
        "serial": asset.serial_number[:20] or "—",
        "mac": asset.mac_address[:17] or "—",
        "model": asset.model_number[:20] or "—",
        "location": asset.location[:20] or "—",
        "comments": comments,
    }
    if show_mac_2:
        cells["mac_2"] = asset.mac_address_2[:17] or "—"
    return cells
