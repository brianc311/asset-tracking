import uuid

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.assets.models import Asset
from apps.scan.forms import ScanAssetForm


def _get_session_key(request):
    key = request.session.get("scan_session_key")
    if not key:
        key = f"scan_{uuid.uuid4().hex[:12]}"
        request.session["scan_session_key"] = key
        request.session[key] = []
    return key


def _get_session_assets(request):
    key = _get_session_key(request)
    ids = request.session.get(key, [])
    return Asset.objects.filter(pk__in=ids).order_by("-created_at")


@login_required
def scan_home(request):
    if not request.user.can_manage_assets():
        return redirect("accounts:dashboard")

    session_assets = _get_session_assets(request)
    session_key = _get_session_key(request)
    return render(
        request,
        "scan/home.html",
        {
            "session_assets": session_assets,
            "session_total": session_assets.count(),
            "session_key": session_key,
        },
    )


@login_required
def scan_register(request, barcode=None):
    if not request.user.can_manage_assets():
        return redirect("accounts:dashboard")

    existing = None
    if barcode:
        existing = Asset.objects.filter(barcode_value=barcode).first()

    if request.method == "POST":
        if existing:
            form = ScanAssetForm(request.POST, request.FILES, instance=existing)
        else:
            form = ScanAssetForm(request.POST, request.FILES)
        if form.is_valid():
            asset = form.save(commit=False)
            if not existing:
                asset.created_by = request.user
                if not asset.barcode_value:
                    asset.barcode_value = barcode or Asset.generate_barcode_value()
            asset.updated_by = request.user
            asset.save()

            session_key = _get_session_key(request)
            ids = request.session.get(session_key, [])
            if asset.pk not in ids:
                ids.append(asset.pk)
            request.session[session_key] = ids
            request.session.modified = True

            return redirect("scan:home")
    else:
        initial = {"barcode_value": barcode} if barcode else {}
        form = ScanAssetForm(instance=existing, initial=initial if not existing else None)

    return render(
        request,
        "scan/register.html",
        {
            "form": form,
            "barcode": barcode,
            "existing": existing,
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
