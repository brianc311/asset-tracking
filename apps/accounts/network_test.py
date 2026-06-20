from django.http import HttpResponse


def network_ping(request):
    """Public endpoint to verify phone can reach the laptop over Wi-Fi."""
    host = request.get_host()
    return HttpResponse(
        f"Asset Tracking is reachable.\n"
        f"Your device connected as: {host}\n"
        f"Client IP: {request.META.get('REMOTE_ADDR', 'unknown')}\n",
        content_type="text/plain",
    )
