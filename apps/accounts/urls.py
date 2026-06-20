from django.urls import path

from apps.accounts import views
from apps.accounts.network_test import network_ping

app_name = "accounts"

urlpatterns = [
    path("ping/", network_ping, name="network_ping"),
    path("login/", views.AppLoginView.as_view(), name="login"),
    path("logout/", views.AppLogoutView.as_view(), name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("api/theme/", views.set_theme, name="set_theme"),
]
