from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.branding.forms import BrandingForm
from apps.branding.models import SiteBranding


def branding_context(request):
    branding = SiteBranding.get_solo()
    theme = "system"
    if request.user.is_authenticated:
        theme = request.user.theme_preference
    return {"branding": branding, "user_theme": theme}


class BrandingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.branding = SiteBranding.get_solo()
        return self.get_response(request)


@login_required
def branding_console(request):
    if not request.user.can_manage_branding():
        return redirect("accounts:dashboard")

    branding = SiteBranding.get_solo()
    if request.method == "POST":
        form = BrandingForm(request.POST, request.FILES, instance=branding)
        if form.is_valid():
            form.save()
            return redirect("branding:console")
    else:
        form = BrandingForm(instance=branding)

    return render(request, "branding/console.html", {"form": form})
