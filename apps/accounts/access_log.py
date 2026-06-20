def get_client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or "0.0.0.0"


def log_access(request, event_type, *, username=""):
    from apps.accounts.models import AccessLog

    if not request.path.startswith("/static/") and not request.path.startswith("/media/"):
        AccessLog.objects.create(
            ip_address=get_client_ip(request),
            event_type=event_type,
            path=request.path[:512],
            username=(username or "")[:150],
            user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:512],
        )
