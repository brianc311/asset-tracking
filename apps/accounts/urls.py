from django.urls import path

from apps.accounts import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.AppLoginView.as_view(), name="login"),
    path("logout/", views.AppLogoutView.as_view(), name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("api/theme/", views.set_theme, name="set_theme"),
]
