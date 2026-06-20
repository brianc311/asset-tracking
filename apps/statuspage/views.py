from django.contrib import messages
from django.db import connection
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.statuspage.forms import ComponentForm, ComponentUpdateForm, IncidentForm
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
    elif components.filter(status=SystemComponent.Status.OFFLINE).exists():
        overall = "major"
    elif (
        active_incidents.exists()
        or components.filter(status=SystemComponent.Status.DEGRADED).exists()
    ):
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
    component_errors = {}

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
                messages.success(request, "Incident posted.")
                return redirect("statuspage:manage")
        elif form_type == "component":
            component_form = ComponentForm(request.POST)
            if component_form.is_valid():
                component_form.save()
                messages.success(request, "Component added.")
                return redirect("statuspage:manage")
        elif form_type == "update_components":
            updated = 0
            for component in components:
                field_prefix = f"component_{component.pk}"
                form = ComponentUpdateForm(
                    {
                        "status": request.POST.get(f"{field_prefix}_status", component.status),
                        "status_reason": request.POST.get(f"{field_prefix}_status_reason", ""),
                    }
                )
                if form.is_valid():
                    component.status = form.cleaned_data["status"]
                    component.status_reason = form.cleaned_data["status_reason"]
                    component.save(update_fields=["status", "status_reason"])
                    updated += 1
                else:
                    component_errors[component.pk] = form
            if component_errors:
                messages.error(request, "Fix the errors below and try again.")
            else:
                messages.success(request, f"Updated {updated} component(s).")
                return redirect("statuspage:manage")

    if incident_form is None:
        incident_form = IncidentForm(initial={"started_at": timezone.now()})
    if component_form is None:
        component_form = ComponentForm()

    component_rows = []
    for component in components:
        field_prefix = f"component_{component.pk}"
        if request.method == "POST" and request.POST.get("form_type") == "update_components":
            status = request.POST.get(f"{field_prefix}_status", component.status)
            reason = request.POST.get(f"{field_prefix}_status_reason", "")
        else:
            status = component.status
            reason = component.status_reason
        error_form = component_errors.get(component.pk)
        component_rows.append(
            {
                "component": component,
                "status": status,
                "reason": reason,
                "errors": error_form.errors if error_form else None,
            }
        )

    return render(
        request,
        "statuspage/manage.html",
        {
            "incidents": incidents,
            "components": components,
            "component_rows": component_rows,
            "component_errors": component_errors,
            "incident_form": incident_form,
            "component_form": component_form,
        },
    )
