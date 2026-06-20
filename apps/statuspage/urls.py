from django.urls import path

from apps.statuspage import views

app_name = "statuspage"

urlpatterns = [
    path("", views.status_public, name="public"),
    path("manage/", views.status_manage, name="manage"),
]
