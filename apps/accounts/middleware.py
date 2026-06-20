from django.http import HttpResponseForbidden
from django.shortcuts import render

from apps.accounts.access_log import get_client_ip, log_access
from apps.accounts.models import AccessLog, BlockedIP


class BlockedIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = get_client_ip(request)
        if ip and BlockedIP.objects.filter(ip_address=ip, is_active=True).exists():
            log_access(request, AccessLog.EventType.ACCESS_BLOCKED)
            return render(
                request,
                "accounts/blocked.html",
                {"ip_address": ip},
                status=403,
            )
        return self.get_response(request)


class AccessLogMiddleware:
    SKIP_PREFIXES = ("/static/", "/media/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        path = request.path
        if any(path.startswith(prefix) for prefix in self.SKIP_PREFIXES):
            return response
        if request.method != "GET":
            return response
        log_access(
            request,
            AccessLog.EventType.PAGE_VIEW,
            username=request.user.username if request.user.is_authenticated else "",
        )
        return response
