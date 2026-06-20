from django.urls import path

from apps.accounts import security_views, views
from apps.accounts.network_test import network_ping

app_name = "accounts"

urlpatterns = [
    path("ping/", network_ping, name="network_ping"),
    path("login/", views.AppLoginView.as_view(), name="login"),
    path("logout/", views.AppLogoutView.as_view(), name="logout"),
    path("security/", security_views.security_logs, name="security_logs"),
    path("security/block/", security_views.block_ip, name="block_ip"),
    path("security/unblock/<int:pk>/", security_views.unblock_ip, name="unblock_ip"),
    path("", views.dashboard, name="dashboard"),
    path("api/theme/", views.set_theme, name="set_theme"),
]
