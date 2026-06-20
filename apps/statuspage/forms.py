from django import forms

from apps.statuspage.models import Incident, SystemComponent


class IncidentForm(forms.ModelForm):
    class Meta:
        model = Incident
        fields = [
            "title",
            "description",
            "cause",
            "resolution",
            "severity",
            "status",
            "is_public",
            "started_at",
            "resolved_at",
            "affected_components",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input"}),
            "description": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
            "cause": forms.Textarea(attrs={"class": "form-input", "rows": 2}),
            "resolution": forms.Textarea(attrs={"class": "form-input", "rows": 2}),
            "severity": forms.Select(attrs={"class": "form-input"}),
            "status": forms.Select(attrs={"class": "form-input"}),
            "started_at": forms.DateTimeInput(attrs={"class": "form-input", "type": "datetime-local"}),
            "resolved_at": forms.DateTimeInput(attrs={"class": "form-input", "type": "datetime-local"}),
            "affected_components": forms.CheckboxSelectMultiple(),
        }


class ComponentForm(forms.ModelForm):
    class Meta:
        model = SystemComponent
        fields = ["name", "description", "status", "display_order"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "description": forms.TextInput(attrs={"class": "form-input"}),
            "status": forms.Select(attrs={"class": "form-input"}),
            "display_order": forms.NumberInput(attrs={"class": "form-input"}),
        }
