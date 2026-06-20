from django.urls import path

from apps.scan import views

app_name = "scan"

urlpatterns = [
    path("", views.scan_home, name="home"),
    path("start/", views.start_scan, name="start"),
    path("register/", views.scan_register, name="register"),
    path("register/<str:barcode>/", views.scan_register, name="register"),
    path("clear/", views.clear_session, name="clear"),
    path("end/", views.end_scan, name="end"),
]
