from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class SystemComponent(models.Model):
    class Status(models.TextChoices):
        OPERATIONAL = "operational", "Operational"
        DEGRADED = "degraded", "Degraded"
        OFFLINE = "offline", "Offline"

    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPERATIONAL,
    )
    status_reason = models.TextField(
        blank=True,
        help_text="Shown on the public status page when degraded or offline.",
    )
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name


class Incident(models.Model):
    class Severity(models.TextChoices):
        INFO = "info", "Informational"
        MINOR = "minor", "Minor"
        MAJOR = "major", "Major"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        INVESTIGATING = "investigating", "Investigating"
        IDENTIFIED = "identified", "Identified"
        MONITORING = "monitoring", "Monitoring"
        RESOLVED = "resolved", "Resolved"

    title = models.CharField(max_length=255)
    description = models.TextField()
    cause = models.TextField(blank=True, help_text="Root cause of the outage.")
    resolution = models.TextField(blank=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.MINOR)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INVESTIGATING)
    is_public = models.BooleanField(default=True)
    started_at = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    affected_components = models.ManyToManyField(SystemComponent, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return self.title

    @property
    def is_active(self):
        return self.status != self.Status.RESOLVED
