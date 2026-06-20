from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

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
@require_POST
def unblock_ip(request, pk):
    blocked = get_object_or_404(BlockedIP, pk=pk)
    blocked.is_active = False
    blocked.save(update_fields=["is_active"])
    messages.success(request, f"Unblocked {blocked.ip_address}.")
    return redirect("accounts:security_logs")
