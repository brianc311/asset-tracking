from django.urls import path

from apps.scan import batch
from apps.scan import views

app_name = "scan"

urlpatterns = [
    path("", views.scan_home, name="home"),
    path("batch/", batch.batch_home, name="batch_home"),
    path("batch/start/", batch.batch_start, name="batch_start"),
    path("batch/save/", batch.batch_save, name="batch_save"),
    path("batch/archive/", batch.batch_archive, name="batch_archive"),
    path("batch/end/", batch.batch_end, name="batch_end"),
    path("batch/report/", batch.batch_report, name="batch_report"),
    path("batch/labels/", batch.batch_labels, name="batch_labels"),
    path("start/", views.start_scan, name="start"),
    path("register/", views.scan_register, name="register"),
    path("register/<str:barcode>/", views.scan_register, name="register"),
    path("clear/", views.clear_session, name="clear"),
    path("end/", views.end_scan, name="end"),
]
