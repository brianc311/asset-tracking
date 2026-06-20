from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.assets.barcode_utils import assets_pdf_response, barcode_image_response
from apps.assets.forms import AssetForm, BulkActionForm
from apps.assets.models import Asset


def _require_asset_access(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if not request.user.can_manage_assets() and request.method != "GET":
            return redirect("assets:list")
        return view_func(request, *args, **kwargs)
    return login_required(wrapper)


@login_required
def asset_list(request):
    show_archived = request.GET.get("archived") == "1"
    q = request.GET.get("q", "").strip()
    qs = Asset.objects.filter(is_archived=show_archived)
    if q:
        filters = (
            Q(product_name__icontains=q)
            | Q(barcode_value__icontains=q)
            | Q(serial_number__icontains=q)
            | Q(model_number__icontains=q)
        )
        if q.isdigit():
            filters |= Q(asset_number=int(q))
        qs = qs.filter(filters)
    return render(
        request,
        "assets/list.html",
        {"assets": qs, "show_archived": show_archived, "query": q},
    )


@_require_asset_access
def asset_create(request):
    if request.method == "POST":
        form = AssetForm(request.POST, request.FILES)
        if form.is_valid():
            asset = form.save(commit=False)
            asset.created_by = request.user
            asset.updated_by = request.user
            asset.save()
            return redirect("assets:detail", pk=asset.pk)
    else:
        form = AssetForm()
    return render(request, "assets/form.html", {"form": form, "action": "Create"})


@login_required
def asset_detail(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    scan_url = asset.get_scan_url(request)
    return render(request, "assets/detail.html", {"asset": asset, "scan_url": scan_url})


@_require_asset_access
def asset_edit(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    if request.method == "POST":
        form = AssetForm(request.POST, request.FILES, instance=asset)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = request.user
            obj.save()
            return redirect("assets:detail", pk=obj.pk)
    else:
        form = AssetForm(instance=asset)
    return render(request, "assets/form.html", {"form": form, "action": "Edit", "asset": asset})


@login_required
def asset_barcode(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    return barcode_image_response(asset)


@_require_asset_access
@require_POST
def bulk_action(request):
    form = BulkActionForm(request.POST)
    if not form.is_valid():
        return redirect("assets:list")

    ids = [int(x) for x in form.cleaned_data["asset_ids"].split(",") if x.strip().isdigit()]
    assets = Asset.objects.filter(pk__in=ids)
    action = form.cleaned_data["action"]

    if action == BulkActionForm.ACTION_ARCHIVE:
        assets.update(is_archived=True, archived_at=timezone.now())
    elif action == BulkActionForm.ACTION_DELETE:
        if request.user.is_admin_role:
            assets.delete()

    return redirect("assets:list")


@login_required
def print_report(request):
    ids_param = request.GET.get("ids", "")
    session_key = request.GET.get("session", "")

    if ids_param:
        ids = [int(x) for x in ids_param.split(",") if x.strip().isdigit()]
        assets = Asset.objects.filter(pk__in=ids, is_archived=False)
        title = "Selected Assets Report"
    elif session_key and session_key in request.session:
        ids = request.session[session_key]
        assets = Asset.objects.filter(pk__in=ids)
        site_name = request.GET.get("site", "").strip()
        if not site_name:
            meta = request.session.get("scan_sessions_meta", {}).get(session_key, {})
            site_name = meta.get("site_name", "")
        title = f"Scan Session — {site_name}" if site_name else "Scan Session Report"
    else:
        assets = Asset.objects.filter(is_archived=False)
        title = "All Active Assets Report"

    export = request.GET.get("export")
    if export == "pdf":
        return assets_pdf_response(assets, title=title)

    return render(
        request,
        "assets/print_report.html",
        {"assets": assets, "title": title, "total": assets.count()},
    )
