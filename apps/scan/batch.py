import uuid
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from apps.assets.barcode_utils import barcode_data_uri, batch_report_pdf_response
from apps.assets.models import Asset
from apps.assets.product_types import get_known_product_names
from apps.assets.site_names import get_known_site_names
from apps.scan.forms import BatchItemForm, StartBatchForm

BATCH_KEY = "batch_session_key"
BATCH_META = "batch_sessions_meta"


def asset_manager_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.can_manage_assets():
            return redirect("accounts:dashboard")
        return view_func(request, *args, **kwargs)

    return wrapped


def _get_meta(request, key):
    return request.session.get(BATCH_META, {}).get(key, {})


def get_batch_session(request):
    key = request.session.get(BATCH_KEY)
    return request.session.get(key, []) if key else []


def require_active_batch(request):
    key = request.session.get(BATCH_KEY)
    meta = _get_meta(request, key) if key else {}
    site = (meta.get("site_name") or "").strip()
    product = (meta.get("product_name") or "").strip()
    if not key or not site or not product:
        return None, None, None, None
    return key, meta, site, product


def _session_assets(request, key):
    ids = request.session.get(key, [])
    return Asset.objects.filter(pk__in=ids, is_archived=False).order_by("-created_at")


@login_required
@asset_manager_required
def batch_start(request):
    form = StartBatchForm(
        request.POST or None,
        known_site_names=get_known_site_names(request),
        known_product_names=get_known_product_names(),
    )
    if request.method == "POST" and form.is_valid():
        key = f"batch_{uuid.uuid4().hex[:12]}"
        request.session[BATCH_KEY] = key
        request.session[key] = []
        meta = request.session.get(BATCH_META, {})
        meta[key] = {
            "site_name": form.cleaned_data["site_name"],
            "product_name": form.cleaned_data["product_name"],
            "started_at": timezone.now().isoformat(),
        }
        request.session[BATCH_META] = meta
        request.session.modified = True
        return redirect("scan:batch_home")
    return render(request, "scan/batch_start.html", {"form": form})


@login_required
@asset_manager_required
def batch_home(request):
    key, meta, site, product = require_active_batch(request)
    if not site:
        return redirect("scan:batch_start")
    started = meta.get("started_at")
    started_display = ""
    if started:
        parsed = parse_datetime(started)
        if parsed:
            started_display = timezone.localtime(parsed).strftime("%b %d, %Y %I:%M %p")
    return render(
        request,
        "scan/batch_home.html",
        {
            "form": BatchItemForm(),
            "assets": _session_assets(request, key),
            "site_name": site,
            "product_name": product,
            "started_at_display": started_display,
        },
    )


@login_required
@require_POST
def batch_save(request):
    if not request.user.can_manage_assets():
        return redirect("accounts:dashboard")
    key, meta, site, product = require_active_batch(request)
    if not site:
        return redirect("scan:batch_start")

    form = BatchItemForm(request.POST)
    if form.is_valid():
        asset = Asset(
            site_name=site,
            product_name=product,
            serial_number=form.cleaned_data["serial_number"].strip(),
            mac_address=form.cleaned_data["mac_address"],
            mac_address_2=form.cleaned_data["mac_address_2"],
            barcode_value=Asset.generate_barcode_value(),
            created_by=request.user,
            updated_by=request.user,
        )
        try:
            asset.full_clean()
            asset.save()
        except ValidationError as exc:
            if hasattr(exc, "error_dict"):
                for field_name, errors in exc.error_dict.items():
                    target_field = field_name if field_name in form.fields else None
                    for error in errors:
                        form.add_error(target_field, error)
            else:
                form.add_error(None, exc)
        else:
            ids = request.session.get(key, [])
            ids.append(asset.pk)
            request.session[key] = ids
            request.session.modified = True
            return redirect("scan:batch_home")

    started = meta.get("started_at")
    started_display = ""
    if started:
        parsed = parse_datetime(started)
        if parsed:
            started_display = timezone.localtime(parsed).strftime("%b %d, %Y %I:%M %p")
    return render(
        request,
        "scan/batch_home.html",
        {
            "form": form,
            "assets": _session_assets(request, key),
            "site_name": site,
            "product_name": product,
            "started_at_display": started_display,
        },
        status=200,
    )


@login_required
@require_POST
def batch_archive(request):
    if not request.user.can_manage_assets():
        return redirect("accounts:dashboard")
    key, meta, site, product = require_active_batch(request)
    if not site:
        return redirect("scan:batch_start")
    ids = [int(value) for value in request.POST.get("asset_ids", "").split(",") if value.strip().isdigit()]
    Asset.objects.filter(pk__in=ids, site_name=site).update(
        is_archived=True,
        archived_at=timezone.now(),
    )
    return redirect("scan:batch_home")


@login_required
@asset_manager_required
@require_POST
def batch_end(request):
    key = request.session.get(BATCH_KEY)
    if key:
        meta = request.session.get(BATCH_META, {})
        meta.pop(key, None)
        request.session.pop(key, None)
        request.session[BATCH_META] = meta
        request.session.pop(BATCH_KEY, None)
        request.session.modified = True
    return redirect("scan:batch_start")


def _batch_target_assets(request):
    key, meta, site, product = require_active_batch(request)
    if not site:
        return None, None, None, None, Asset.objects.none()
    ids_param = request.GET.get("ids") or request.POST.get("asset_ids") or ""
    ids = [int(value) for value in ids_param.split(",") if value.strip().isdigit()]
    assets = Asset.objects.filter(is_archived=False, site_name=site, product_name=product)
    if ids:
        assets = assets.filter(pk__in=ids)
    return key, meta, site, product, assets.order_by("created_at")


@login_required
@asset_manager_required
def batch_report(request):
    _, _, site, product, assets = _batch_target_assets(request)
    if not site:
        return redirect("scan:batch_start")
    if request.GET.get("export") == "pdf":
        return batch_report_pdf_response(assets, site_name=site, product_name=product)

    pdf_params = request.GET.copy()
    pdf_params["export"] = "pdf"
    rows = []
    for asset in assets:
        rows.append(
            {
                "asset": asset,
                "serial_barcode": barcode_data_uri(asset.serial_number) if asset.serial_number else "",
                "mac_barcode": barcode_data_uri(asset.mac_address) if asset.mac_address else "",
                "mac2_barcode": barcode_data_uri(asset.mac_address_2) if asset.mac_address_2 else "",
            }
        )
    return render(
        request,
        "scan/batch_report.html",
        {
            "rows": rows,
            "site_name": site,
            "product_name": product,
            "total": len(rows),
            "pdf_query": pdf_params.urlencode(),
        },
    )


@login_required
@asset_manager_required
def batch_labels(request):
    _, _, site, product, assets = _batch_target_assets(request)
    if not site:
        return redirect("scan:batch_start")

    mode = request.GET.get("mode", "device")
    labels = []
    if mode == "value":
        for asset in assets:
            if asset.serial_number:
                labels.append(
                    {
                        "title": "Serial",
                        "value": asset.serial_number,
                        "barcode": barcode_data_uri(asset.serial_number),
                    }
                )
            if asset.mac_address:
                labels.append(
                    {
                        "title": "MAC",
                        "value": asset.mac_address,
                        "barcode": barcode_data_uri(asset.mac_address),
                    }
                )
            if asset.mac_address_2:
                labels.append(
                    {
                        "title": "MAC 2",
                        "value": asset.mac_address_2,
                        "barcode": barcode_data_uri(asset.mac_address_2),
                    }
                )
    else:
        for asset in assets:
            labels.append(
                {
                    "title": f"{asset.product_name} — {asset.site_name}",
                    "value": asset.serial_number,
                    "extra": " / ".join(
                        mac for mac in (asset.mac_address, asset.mac_address_2) if mac
                    ),
                    "barcode": barcode_data_uri(asset.serial_number) if asset.serial_number else "",
                    "mac_barcode": barcode_data_uri(asset.mac_address) if asset.mac_address else "",
                    "mac2_barcode": barcode_data_uri(asset.mac_address_2) if asset.mac_address_2 else "",
                }
            )

    return render(
        request,
        "scan/batch_labels.html",
        {"labels": labels, "mode": mode, "site_name": site, "product_name": product},
    )
