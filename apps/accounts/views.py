from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from apps.accounts.forms import RecaptchaAuthenticationForm
from apps.assets.models import Asset


@method_decorator(never_cache, name="dispatch")
class AppLoginView(LoginView):
    template_name = "accounts/login.html"
    form_class = RecaptchaAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("accounts:dashboard")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        key = settings.RECAPTCHA_PUBLIC_KEY or ""
        context["recaptcha_key_prefix"] = key[:12]
        context["recaptcha_is_test_key"] = key.startswith("6LeIxAcT")
        return context


class AppLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")


@login_required
def dashboard(request):
    assets = Asset.objects.filter(is_archived=False)
    context = {
        "total_assets": assets.count(),
        "recent_assets": assets.order_by("-created_at")[:5],
        "archived_count": Asset.objects.filter(is_archived=True).count(),
    }
    return render(request, "accounts/dashboard.html", context)


@login_required
@require_POST
def set_theme(request):
    theme = request.POST.get("theme", "system")
    if theme in ("light", "dark", "system"):
        request.user.theme_preference = theme
        request.user.save(update_fields=["theme_preference"])
    return JsonResponse({"ok": True, "theme": theme})
