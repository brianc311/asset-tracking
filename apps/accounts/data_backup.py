from __future__ import annotations

import json
from datetime import datetime, timezone

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.models import BlockedIP
from apps.assets.models import Asset

BACKUP_FORMAT = "asset-tracking-backup"
BACKUP_VERSION = 1
ASSET_FIELDS = (
    "barcode_value",
    "barcode_type",
    "product_name",
    "device_name",
    "serial_number",
    "mac_address",
    "mac_address_2",
    "model_number",
    "site_name",
    "location",
    "comments",
    "is_archived",
)


def export_payload() -> dict:
    assets = []
    for asset in Asset.objects.all().order_by("asset_number", "pk"):
        row = {field: getattr(asset, field) for field in ASSET_FIELDS}
        row["archived_at"] = asset.archived_at.isoformat() if asset.archived_at else None
        assets.append(row)
    blocked = [
        {
            "ip_address": item.ip_address,
            "reason": item.reason,
            "is_active": item.is_active,
        }
        for item in BlockedIP.objects.all().order_by("pk")
    ]
    return {
        "format": BACKUP_FORMAT,
        "version": BACKUP_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "assets": assets,
        "blocked_ips": blocked,
    }


def parse_backup(raw) -> dict:
    if hasattr(raw, "read"):
        raw = raw.read()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    try:
        payload = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValidationError("That file is not valid JSON.") from exc
    if not isinstance(payload, dict) or payload.get("format") != BACKUP_FORMAT:
        raise ValidationError("That file is not an Asset Tracking export.")
    if not isinstance(payload.get("assets"), list) or not isinstance(
        payload.get("blocked_ips", []), list
    ):
        raise ValidationError("That export file is missing asset or blocked-IP lists.")
    return payload


def import_payload(payload: dict, *, user) -> dict:
    added_assets = 0
    skipped_assets = 0
    added_ips = 0
    skipped_ips = 0
    problems = []

    existing_barcodes = set(
        Asset.objects.values_list("barcode_value", flat=True)
    )
    existing_ips = set(BlockedIP.objects.values_list("ip_address", flat=True))

    for index, row in enumerate(payload.get("assets") or [], start=1):
        if not isinstance(row, dict):
            skipped_assets += 1
            problems.append(f"Asset {index}: skipped (invalid row).")
            continue
        barcode = (row.get("barcode_value") or "").strip()
        if not barcode:
            skipped_assets += 1
            problems.append(f"Asset {index}: skipped (no barcode).")
            continue
        if barcode in existing_barcodes:
            skipped_assets += 1
            continue
        asset = Asset(
            barcode_value=barcode,
            barcode_type=row.get("barcode_type") or Asset.BarcodeType.QR,
            product_name=(row.get("product_name") or "").strip() or "Imported",
            device_name=row.get("device_name") or "",
            serial_number=row.get("serial_number") or "",
            mac_address=row.get("mac_address") or "",
            mac_address_2=row.get("mac_address_2") or "",
            model_number=row.get("model_number") or "",
            site_name=row.get("site_name") or "",
            location=row.get("location") or "",
            comments=row.get("comments") or "",
            is_archived=bool(row.get("is_archived")),
            created_by=user,
        )
        try:
            with transaction.atomic():
                asset.full_clean()
                asset.save()
        except ValidationError as exc:
            skipped_assets += 1
            problems.append(f"{barcode}: skipped ({_first_error(exc)}).")
            continue
        existing_barcodes.add(barcode)
        added_assets += 1

    for index, row in enumerate(payload.get("blocked_ips") or [], start=1):
        if not isinstance(row, dict):
            skipped_ips += 1
            continue
        ip_address = (row.get("ip_address") or "").strip()
        if not ip_address:
            skipped_ips += 1
            continue
        if ip_address in existing_ips:
            skipped_ips += 1
            continue
        try:
            with transaction.atomic():
                BlockedIP.objects.create(
                    ip_address=ip_address,
                    reason=row.get("reason") or "",
                    is_active=row.get("is_active", True),
                    blocked_by=user,
                )
        except Exception as exc:
            skipped_ips += 1
            problems.append(f"IP {ip_address}: skipped ({exc}).")
            continue
        existing_ips.add(ip_address)
        added_ips += 1

    return {
        "added_assets": added_assets,
        "skipped_assets": skipped_assets,
        "added_ips": added_ips,
        "skipped_ips": skipped_ips,
        "problems": problems[:20],
    }


def _first_error(exc: ValidationError) -> str:
    if getattr(exc, "message_dict", None):
        for messages in exc.message_dict.values():
            if messages:
                return str(messages[0])
    if getattr(exc, "messages", None):
        return str(exc.messages[0])
    return str(exc)
