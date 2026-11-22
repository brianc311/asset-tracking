import json
from datetime import datetime, timezone

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.data_backup import export_payload, import_payload, parse_backup
from apps.accounts.models import AccessLog, BlockedIP


def _require_security_access(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.can_view_access_logs():
            return redirect("accounts:dashboard")
        return view_func(request, *args, **kwargs)

    return wrapper


@_require_security_access
def security_logs(request):
    logs = AccessLog.objects.all()[:500]
    blocked = BlockedIP.objects.filter(is_active=True)
    ip_summary = (
        AccessLog.objects.values("ip_address")
        .annotate(total=Count("id"))
        .order_by("-total")[:20]
    )
    failed_logins = (
        AccessLog.objects.filter(event_type=AccessLog.EventType.LOGIN_FAILED)
        .values("ip_address")
        .annotate(total=Count("id"))
        .order_by("-total")[:20]
    )
    return render(
        request,
        "accounts/security_logs.html",
        {
            "logs": logs,
            "blocked_ips": blocked,
            "ip_summary": ip_summary,
            "failed_logins": failed_logins,
        },
    )


@_require_security_access
@require_POST
def block_ip(request):
    ip_address = request.POST.get("ip_address", "").strip()
    reason = request.POST.get("reason", "").strip()
    if not ip_address:
        messages.error(request, "IP address is required.")
        return redirect("accounts:security_logs")

    blocked, created = BlockedIP.objects.update_or_create(
        ip_address=ip_address,
        defaults={
            "reason": reason,
            "is_active": True,
            "blocked_by": request.user,
        },
    )
    if created:
        messages.success(request, f"Blocked {ip_address}.")
    else:
        messages.success(request, f"Updated block for {ip_address}.")
    return redirect("accounts:security_logs")


@_require_security_access
@require_GET
def export_data(request):
    payload = export_payload()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    response = HttpResponse(
        json.dumps(payload, indent=2),
        content_type="application/json",
    )
    response["Content-Disposition"] = f'attachment; filename="asset-tracking-data-{stamp}.json"'
    return response


@_require_security_access
@require_POST
def import_data(request):
    upload = request.FILES.get("backup_file")
    if not upload:
        messages.error(request, "Choose an export file to import.")
        return redirect("accounts:security_logs")
    try:
        payload = parse_backup(upload)
        result = import_payload(payload, user=request.user)
    except ValidationError as exc:
        messages.error(request, exc.messages[0] if exc.messages else str(exc))
        return redirect("accounts:security_logs")
    messages.success(
        request,
        (
            f"Added {result['added_assets']} asset(s), skipped {result['skipped_assets']} existing. "
            f"Added {result['added_ips']} blocked IP(s), skipped {result['skipped_ips']} existing."
        ),
    )
    for problem in result["problems"]:
        messages.warning(request, problem)
    return redirect("accounts:security_logs")


@_require_security_access
@require_POST
def unblock_ip(request, pk):
    blocked = get_object_or_404(BlockedIP, pk=pk)
    blocked.is_active = False
    blocked.save(update_fields=["is_active"])
    messages.success(request, f"Unblocked {blocked.ip_address}.")
    return redirect("accounts:security_logs")
