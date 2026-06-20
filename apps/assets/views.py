from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.assets.barcode_utils import assets_pdf_response, barcode_image_response
from apps.assets.email_reports import EmailNotConfiguredError, email_is_configured, send_site_asset_report
from apps.assets.forms import AssetForm, BulkActionForm, SiteReportEmailForm
from apps.assets.models import Asset
from apps.assets.site_names import get_known_site_names, get_site_names_with_assets


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
            | Q(site_name__icontains=q)
            | Q(location__icontains=q)
        )
        if q.isdigit():
            filters |= Q(asset_number=int(q))
        qs = qs.filter(filters)
    return render(
        request,
        "assets/list.html",
        {"assets": qs, "show_archived": show_archived, "query": q},
    )


def _active_scan_site_name(request):
    session_key = request.session.get("scan_session_key")
    if not session_key:
        return ""
    meta = request.session.get("scan_sessions_meta", {}).get(session_key, {})
    return (meta.get("site_name") or "").strip()


@_require_asset_access
def asset_create(request):
    known_sites = get_known_site_names(request)
    default_site = _active_scan_site_name(request)
    if request.method == "POST":
        form = AssetForm(
            request.POST,
            request.FILES,
            known_site_names=known_sites,
            default_site_name=default_site,
        )
        if form.is_valid():
            asset = form.save(commit=False)
            asset.created_by = request.user
            asset.updated_by = request.user
            asset.save()
            return redirect("assets:detail", pk=asset.pk)
    else:
        form = AssetForm(known_site_names=known_sites, default_site_name=default_site)
    return render(
        request,
        "assets/form.html",
        {"form": form, "action": "Create", "known_site_names": known_sites},
    )


@login_required
def asset_detail(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    scan_url = asset.get_scan_url(request)
    return render(request, "assets/detail.html", {"asset": asset, "scan_url": scan_url})


@_require_asset_access
def asset_edit(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    known_sites = get_known_site_names(request)
    if request.method == "POST":
        form = AssetForm(request.POST, request.FILES, instance=asset, known_site_names=known_sites)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = request.user
            obj.save()
            return redirect("assets:detail", pk=obj.pk)
    else:
        form = AssetForm(instance=asset, known_site_names=known_sites)
    return render(
        request,
        "assets/form.html",
        {"form": form, "action": "Edit", "asset": asset, "known_site_names": known_sites},
    )


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
    site_filter = request.GET.get("site", "").strip()

    if ids_param:
        ids = [int(x) for x in ids_param.split(",") if x.strip().isdigit()]
        assets = Asset.objects.filter(pk__in=ids, is_archived=False)
        title = "Selected Assets Report"
    elif site_filter:
        assets = Asset.objects.filter(site_name=site_filter, is_archived=False)
        title = f"Asset Report — {site_filter}"
    elif session_key and session_key in request.session:
        ids = request.session[session_key]
        assets = Asset.objects.filter(pk__in=ids)
        if not site_filter:
            meta = request.session.get("scan_sessions_meta", {}).get(session_key, {})
            site_filter = meta.get("site_name", "")
        title = f"Scan Session — {site_filter}" if site_filter else "Scan Session Report"
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


@_require_asset_access
def email_site_report(request):
    site_names = get_site_names_with_assets()
    default_site = _active_scan_site_name(request)
    default_recipient = request.user.email or ""
    query_site = request.GET.get("site", "").strip()

    form = SiteReportEmailForm(
        request.POST or None,
        site_names=site_names,
        default_site=query_site or default_site,
        default_recipient=default_recipient,
    )

    if request.method == "POST" and form.is_valid():
        if not email_is_configured():
            messages.error(
                request,
                "Gmail is not configured yet. Add EMAIL_HOST_USER and EMAIL_HOST_PASSWORD to your .env file.",
            )
        else:
            site_name = form.cleaned_data["site_name"]
            recipient = form.cleaned_data["recipient"]
            assets = Asset.objects.filter(site_name=site_name, is_archived=False).order_by("asset_number")
            if not assets.exists():
                messages.error(request, f"No active assets found for {site_name}.")
            else:
                try:
                    send_site_asset_report(
                        site_name=site_name,
                        recipient=recipient,
                        assets=assets,
                        sender_name=request.user.get_full_name() or request.user.username,
                    )
                    messages.success(
                        request,
                        f"Report for {site_name} ({assets.count()} items) sent to {recipient}.",
                    )
                    return redirect("assets:list")
                except EmailNotConfiguredError as exc:
                    messages.error(request, str(exc))
                except Exception as exc:
                    messages.error(request, f"Could not send email: {exc}")

    return render(
        request,
        "assets/email_report.html",
        {
            "form": form,
            "email_configured": email_is_configured(),
            "site_names": site_names,
        },
    )
