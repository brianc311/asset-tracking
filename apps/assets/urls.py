from django.urls import path

from apps.assets import views

app_name = "assets"

urlpatterns = [
    path("", views.asset_list, name="list"),
    path("new/", views.asset_create, name="create"),
    path("<int:pk>/", views.asset_detail, name="detail"),
    path("<int:pk>/edit/", views.asset_edit, name="edit"),
    path("<int:pk>/barcode/", views.asset_barcode, name="barcode"),
    path("bulk/", views.bulk_action, name="bulk"),
    path("report/", views.print_report, name="report"),
    path("report/email/", views.email_site_report, name="email_report"),
]
