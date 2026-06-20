import uuid

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from apps.assets.models import Asset
from apps.assets.site_names import get_known_site_names
from apps.scan.forms import ScanAssetForm, StartScanForm

META_KEY = "scan_sessions_meta"


def _get_session_key(request, create=False):
    key = request.session.get("scan_session_key")
    if not key and create:
        key = f"scan_{uuid.uuid4().hex[:12]}"
        request.session["scan_session_key"] = key
        request.session[key] = []
    return key


def _get_scan_meta(request, session_key=None):
    key = session_key or request.session.get("scan_session_key")
    if not key:
        return {}
    meta = request.session.get(META_KEY, {})
    return meta.get(key, {})


def _set_scan_meta(request, session_key, site_name):
    meta = request.session.get(META_KEY, {})
    meta[session_key] = {
        "site_name": site_name.strip(),
        "started_at": timezone.now().isoformat(),
    }
    request.session[META_KEY] = meta
    request.session.modified = True


def _get_session_assets(request):
    key = _get_session_key(request)
    if not key:
        return Asset.objects.none()
    ids = request.session.get(key, [])
    return Asset.objects.filter(pk__in=ids).order_by("-created_at")


def _require_active_scan(request):
    key = _get_session_key(request)
    meta = _get_scan_meta(request, key)
    if not key or not meta.get("site_name"):
        return None, None, None
    return key, meta, meta["site_name"]


@login_required
def start_scan(request):
    if not request.user.can_manage_assets():
        return redirect("accounts:dashboard")

    form = StartScanForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        site_name = form.cleaned_data["site_name"]
        key = f"scan_{uuid.uuid4().hex[:12]}"
        request.session["scan_session_key"] = key
        request.session[key] = []
        _set_scan_meta(request, key, site_name)
        return redirect("scan:home")

    return render(request, "scan/start.html", {"form": form})


@login_required
def scan_home(request):
    if not request.user.can_manage_assets():
        return redirect("accounts:dashboard")

    key, meta, site_name = _require_active_scan(request)
    if not site_name:
        return redirect("scan:start")

    session_assets = _get_session_assets(request)
    started_at = meta.get("started_at")
    started_at_display = None
    if started_at:
        parsed = parse_datetime(started_at)
        if parsed:
            started_at_display = timezone.localtime(parsed).strftime("%b %d, %Y %I:%M %p")

    return render(
        request,
        "scan/home.html",
        {
            "session_assets": session_assets,
            "session_total": session_assets.count(),
            "session_key": key,
            "site_name": site_name,
            "started_at_display": started_at_display,
        },
    )


@login_required
def scan_register(request, barcode=None):
    if not request.user.can_manage_assets():
        return redirect("accounts:dashboard")

    key, meta, site_name = _require_active_scan(request)
    if not site_name:
        return redirect("scan:start")

    existing = None
    if barcode:
        existing = Asset.objects.filter(barcode_value=barcode).first()

    known_sites = get_known_site_names(request)
    if site_name and site_name not in known_sites:
        known_sites = [site_name, *known_sites]

    if request.method == "POST":
        if existing:
            form = ScanAssetForm(
                request.POST,
                request.FILES,
                instance=existing,
                known_site_names=known_sites,
                default_site_name=site_name,
            )
        else:
            form = ScanAssetForm(
                request.POST,
                request.FILES,
                known_site_names=known_sites,
                default_site_name=site_name,
            )
        if form.is_valid():
            asset = form.save(commit=False)
            if not existing:
                asset.created_by = request.user
                if not asset.barcode_value:
                    asset.barcode_value = barcode or Asset.generate_barcode_value()
            if not asset.site_name:
                asset.site_name = site_name
            asset.updated_by = request.user
            asset.save()

            ids = request.session.get(key, [])
            if asset.pk not in ids:
                ids.append(asset.pk)
            request.session[key] = ids
            request.session.modified = True

            return redirect("scan:home")
    else:
        initial = {"barcode_value": barcode} if barcode else {}
        if not existing and site_name:
            initial.setdefault("site_name", site_name)
        form = ScanAssetForm(
            instance=existing,
            initial=initial if not existing else None,
            known_site_names=known_sites,
            default_site_name=site_name,
        )

    return render(
        request,
        "scan/register.html",
        {
            "form": form,
            "barcode": barcode,
            "existing": existing,
            "site_name": site_name,
            "known_site_names": known_sites,
        },
    )


@login_required
@require_POST
def clear_session(request):
    session_key = request.session.get("scan_session_key")
    if session_key:
        request.session[session_key] = []
        request.session.modified = True
    return redirect("scan:home")


@login_required
@require_POST
def end_scan(request):
    session_key = request.session.get("scan_session_key")
    if session_key:
        meta = request.session.get(META_KEY, {})
        meta.pop(session_key, None)
        request.session.pop(session_key, None)
        request.session[META_KEY] = meta
        request.session.pop("scan_session_key", None)
        request.session.modified = True
    return redirect("scan:start")
