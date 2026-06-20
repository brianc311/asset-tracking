from django.urls import path

from apps.branding import views

app_name = "branding"

urlpatterns = [
    path("", views.branding_console, name="console"),
]
