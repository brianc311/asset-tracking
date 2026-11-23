from __future__ import annotations

import csv
import io
from xml.sax.saxutils import escape

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from apps.assets.mac import normalize_mac
from apps.assets.models import Asset
from apps.scan.batch import (
    MODE_CONTINUOUS,
    asset_manager_required,
    require_active_batch,
    _session_assets,
    _update_batch_meta,
)

DRAFTS_SUFFIX = "_drafts"


def drafts_key(session_key: str) -> str:
    return f"{session_key}{DRAFTS_SUFFIX}"


def classify_scan_value(raw: str) -> tuple[str, str]:
    text = (raw or "").strip()
    if not text:
        raise ValueError("Empty scan.")
    try:
        return "mac", normalize_mac(text)
    except ValueError:
        return "serial", text


def _drafts(request, key) -> list[dict]:
    return list(request.session.get(drafts_key(key), []))


def _save_drafts(request, key, rows: list[dict]) -> None:
    request.session[drafts_key(key)] = rows
    request.session.modified = True


def find_duplicate(rows: list[dict], kind: str, value: str, *, site_name: str) -> dict | None:
    if kind == "serial":
        needle = value.casefold()
        for row in rows:
            if (row.get("serial") or "").casefold() == needle:
                return {
                    "row": row["n"],
                    "reason": f"Duplicate of row {row['n']} (serial {row['serial']}).",
                }
        existing = (
            Asset.objects.filter(is_archived=False, serial_number__iexact=value)
            .order_by("asset_number")
            .first()
        )
        if existing:
            number = existing.asset_number or existing.pk
            return {
                "row": None,
                "reason": f"Already in the database (asset #{number}, serial {existing.serial_number}).",
            }
        return None

    for row in rows:
        if row.get("mac") == value or row.get("mac2") == value:
            return {
                "row": row["n"],
                "reason": f"Duplicate of row {row['n']} (MAC {value}).",
            }
    existing = (
        Asset.objects.filter(is_archived=False, mac_address=value)
        .order_by("asset_number")
        .first()
    )
    if not existing:
        existing = (
            Asset.objects.filter(is_archived=False, mac_address_2=value)
            .order_by("asset_number")
            .first()
        )
    if existing:
        number = existing.asset_number or existing.pk
        return {
            "row": None,
            "reason": f"Already in the database (asset #{number}, MAC {value}).",
        }
    return None


def _row_dict(n: int, kind: str, value: str, dup: dict | None) -> dict:
    return {
        "n": n,
        "serial": value if kind == "serial" else "",
        "mac": value if kind == "mac" else "",
        "duplicate": bool(dup),
        "duplicate_of": dup.get("row") if dup else None,
        "duplicate_reason": dup.get("reason") if dup else "",
    }


def _append_scan(request, key, site: str, raw: str) -> dict:
    kind, value = classify_scan_value(raw)
    rows = _drafts(request, key)
    dup = find_duplicate(rows, kind, value, site_name=site)
    row = _row_dict(len(rows) + 1, kind, value, dup)
    rows.append(row)
    _save_drafts(request, key, rows)
    return row


@login_required
@asset_manager_required
def continuous_home(request):
    key, meta, site, product = require_active_batch(request)
    if not site:
        return redirect("scan:batch_start")
    rows = _drafts(request, key)
    last_duplicate = next((row["duplicate_reason"] for row in reversed(rows) if row.get("duplicate")), "")
    return render(
        request,
        "scan/batch_continuous.html",
        {
            "site_name": site,
            "product_name": product,
            "batch_mode": MODE_CONTINUOUS,
            "rows": rows,
            "done": bool(meta.get("continuous_done")),
            "last_duplicate": last_duplicate,
            "add_url": reverse("scan:continuous_add"),
            "finish_url": reverse("scan:continuous_finish"),
            "csv_url": reverse("scan:continuous_export_csv"),
            "excel_url": reverse("scan:continuous_export_excel"),
        },
    )


@login_required
@asset_manager_required
@require_POST
def continuous_add(request):
    key, meta, site, product = require_active_batch(request)
    if not site:
        return JsonResponse({"ok": False, "error": "Start a batch first."}, status=400)
    raw = (request.POST.get("value") or "").strip()
    try:
        row = _append_scan(request, key, site, raw)
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    _update_batch_meta(request, key, continuous_done=False, mode=MODE_CONTINUOUS)
    return JsonResponse({"ok": True, "row": row, "count": row["n"]})


@login_required
@asset_manager_required
@require_POST
def continuous_done(request):
    key, meta, site, product = require_active_batch(request)
    if not site:
        return redirect("scan:batch_start")
    _update_batch_meta(request, key, continuous_done=True, mode=MODE_CONTINUOUS)
    return redirect("scan:batch_home")


@login_required
@asset_manager_required
@require_POST
def continuous_finish(request):
    key, meta, site, product = require_active_batch(request)
    if not site:
        return redirect("scan:batch_start")

    device_name = (request.POST.get("device_name") or "").strip()
    location = (request.POST.get("location") or "").strip()
    comments = (request.POST.get("comments") or "").strip()
    model_number = (request.POST.get("model_number") or "").strip()
    extra_serial = (request.POST.get("serial_number") or "").strip()
    extra_mac = (request.POST.get("mac_address") or "").strip()
    created = 0
    skipped = 0
    for extra in (extra_serial, extra_mac):
        if extra:
            try:
                _append_scan(request, key, site, extra)
            except ValueError:
                skipped += 1

    rows = _drafts(request, key)
    ids = list(request.session.get(key, []))
    for row in rows:
        if row.get("duplicate"):
            skipped += 1
            continue
        asset = Asset(
            site_name=site,
            product_name=product,
            serial_number=row.get("serial") or "",
            mac_address=row.get("mac") or "",
            device_name=device_name,
            location=location,
            comments=comments,
            model_number=model_number,
            barcode_value=Asset.generate_barcode_value(),
            created_by=request.user,
            updated_by=request.user,
        )
        try:
            asset.full_clean()
            asset.save()
        except Exception:
            skipped += 1
            continue
        ids.append(asset.pk)
        created += 1

    request.session[key] = ids
    _save_drafts(request, key, [])
    _update_batch_meta(
        request,
        key,
        continuous_done=False,
        last_device_name=device_name,
        last_location=location,
        mode="quick",
    )
    messages.success(
        request,
        f"Finished continuous scan. Saved {created} asset(s), skipped {skipped} duplicate or invalid row(s).",
    )
    return redirect("scan:batch_home")


def _export_rows(request):
    key, meta, site, product = require_active_batch(request)
    if not site:
        return None, None, None, None
    rows = _drafts(request, key)
    if not rows:
        rows = []
        for index, asset in enumerate(_session_assets(request, key), start=1):
            rows.append(
                {
                    "n": index,
                    "serial": asset.serial_number or "",
                    "mac": asset.mac_address or "",
                    "duplicate": False,
                    "duplicate_reason": "",
                }
            )
    return site, product, rows, meta


def _export_table(rows):
    header = ["Row", "Serial", "MAC", "Duplicate", "Note"]
    body = [
        [
            str(row.get("n") or ""),
            row.get("serial") or "",
            row.get("mac") or "",
            "Yes" if row.get("duplicate") else "No",
            row.get("duplicate_reason") or "",
        ]
        for row in rows
    ]
    return header, body


@login_required
@asset_manager_required
@require_GET
def continuous_export_csv(request):
    site, product, rows, _meta = _export_rows(request)
    if site is None:
        return redirect("scan:batch_start")
    header, body = _export_table(rows)
    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.writer(buffer)
    writer.writerow(["Site", site, "Product", product])
    writer.writerow(header)
    writer.writerows(body)
    response = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="continuous-batch.csv"'
    return response


@login_required
@asset_manager_required
@require_GET
def continuous_export_excel(request):
    site, product, rows, _meta = _export_rows(request)
    if site is None:
        return redirect("scan:batch_start")
    header, body = _export_table(rows)
    html = [
        "<html><head><meta charset='utf-8'></head><body><table>",
        f"<tr><td>Site</td><td>{escape(site)}</td><td>Product</td><td>{escape(product)}</td></tr>",
        "<tr>" + "".join(f"<th>{escape(col)}</th>" for col in header) + "</tr>",
    ]
    for line in body:
        html.append("<tr>" + "".join(f"<td>{escape(col)}</td>" for col in line) + "</tr>")
    html.append("</table></body></html>")
    response = HttpResponse("".join(html), content_type="application/vnd.ms-excel")
    response["Content-Disposition"] = 'attachment; filename="continuous-batch.xls"'
    return response
