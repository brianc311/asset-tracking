from django.contrib.admin import AdminSite
from django.contrib.auth.views import LoginView
from django.urls import path, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from apps.accounts.forms import RecaptchaAuthenticationForm


class RecaptchaAdminLoginView(LoginView):
    template_name = "admin/login.html"
    form_class = RecaptchaAuthenticationForm
    redirect_authenticated_user = True

    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("admin:index")


class RecaptchaAdminSite(AdminSite):
    login_form = RecaptchaAuthenticationForm
    login_template = "admin/login.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("login/", self.login, name="login"),
        ]
        return custom_urls + urls

    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def login(self, request, extra_context=None):
        if request.method == "GET" and request.user.is_authenticated:
            from django.shortcuts import redirect
            return redirect("admin:index")

        context = {
            **self.each_context(request),
            "title": "Log in",
            "app_path": request.get_full_path(),
            "username": request.user.get_username(),
            **(extra_context or {}),
        }

        if request.method == "POST":
            form = RecaptchaAuthenticationForm(request, data=request.POST)
            if form.is_valid():
                from django.contrib.auth import login
                login(request, form.get_user())
                from django.shortcuts import redirect
                return redirect(request.GET.get("next") or reverse_lazy("admin:index"))
            context["form"] = form
        else:
            context["form"] = RecaptchaAuthenticationForm()

        from django.template.response import TemplateResponse
        return TemplateResponse(request, self.login_template, context)


recaptcha_admin_site = RecaptchaAdminSite(name="recaptcha_admin")
