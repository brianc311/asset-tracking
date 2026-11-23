from django.urls import path

from apps.scan import batch
from apps.scan import continuous
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
    path("batch/continuous/add/", continuous.continuous_add, name="continuous_add"),
    path("batch/continuous/done/", continuous.continuous_done, name="continuous_done"),
    path("batch/continuous/finish/", continuous.continuous_finish, name="continuous_finish"),
    path("batch/continuous/export.csv", continuous.continuous_export_csv, name="continuous_export_csv"),
    path("batch/continuous/export.xls", continuous.continuous_export_excel, name="continuous_export_excel"),
    path("start/", views.start_scan, name="start"),
    path("register/", views.scan_register, name="register"),
    path("register/<str:barcode>/", views.scan_register, name="register"),
    path("clear/", views.clear_session, name="clear"),
    path("end/", views.end_scan, name="end"),
]
