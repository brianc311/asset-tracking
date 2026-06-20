from django.db import connection
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.statuspage.forms import ComponentForm, IncidentForm
from apps.statuspage.models import Incident, SystemComponent


def _check_database():
    try:
        connection.ensure_connection()
        return True, "Connected"
    except Exception as exc:
        return False, str(exc)


def status_public(request):
    components = SystemComponent.objects.all()
    active_incidents = Incident.objects.filter(is_public=True).exclude(
        status=Incident.Status.RESOLVED
    )
    recent_incidents = Incident.objects.filter(is_public=True).order_by("-started_at")[:20]

    db_ok, db_msg = _check_database()
    app_ok = True

    overall = "operational"
    if not db_ok or not app_ok:
        overall = "major"
    elif active_incidents.filter(severity__in=["major", "critical"]).exists():
        overall = "major"
    elif active_incidents.exists() or components.filter(status__in=["degraded", "partial"]).exists():
        overall = "degraded"

    return render(
        request,
        "statuspage/public.html",
        {
            "components": components,
            "active_incidents": active_incidents,
            "recent_incidents": recent_incidents,
            "overall_status": overall,
            "db_ok": db_ok,
            "db_msg": db_msg,
            "app_ok": app_ok,
            "checked_at": timezone.now(),
        },
    )


def status_manage(request):
    if not request.user.is_authenticated or not request.user.can_manage_status():
        return redirect("accounts:login")

    incidents = Incident.objects.all()[:50]
    components = SystemComponent.objects.all()

    incident_form = None
    component_form = None

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        if form_type == "incident":
            incident_form = IncidentForm(request.POST)
            if incident_form.is_valid():
                incident = incident_form.save(commit=False)
                incident.created_by = request.user
                incident.save()
                incident_form.save_m2m()
                return redirect("statuspage:manage")
        elif form_type == "component":
            component_form = ComponentForm(request.POST)
            if component_form.is_valid():
                component_form.save()
                return redirect("statuspage:manage")

    if incident_form is None:
        incident_form = IncidentForm(initial={"started_at": timezone.now()})
    if component_form is None:
        component_form = ComponentForm()

    return render(
        request,
        "statuspage/manage.html",
        {
            "incidents": incidents,
            "components": components,
            "incident_form": incident_form,
            "component_form": component_form,
        },
    )
