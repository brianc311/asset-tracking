from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_USER = "super_user", "Super User"
        ADMIN = "admin", "Admin"
        STAFF = "staff", "Staff"
        USER = "user", "User"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
    )
    theme_preference = models.CharField(
        max_length=10,
        choices=[("light", "Light"), ("dark", "Dark"), ("system", "System")],
        default="system",
    )

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return self.username

    @property
    def is_super_user_role(self):
        return self.role == self.Role.SUPER_USER or self.is_superuser

    @property
    def is_admin_role(self):
        return self.role in (self.Role.ADMIN, self.Role.SUPER_USER) or self.is_superuser

    @property
    def is_staff_role(self):
        return self.role in (self.Role.STAFF, self.Role.ADMIN, self.Role.SUPER_USER) or self.is_staff

    def can_manage_branding(self):
        return self.is_super_user_role

    def can_manage_assets(self):
        return self.is_staff_role

    def can_manage_status(self):
        return self.is_admin_role

    def can_manage_users(self):
        return self.is_super_user_role

    def can_view_access_logs(self):
        return self.is_super_user_role


class AccessLog(models.Model):
    class EventType(models.TextChoices):
        PAGE_VIEW = "page_view", "Page view"
        LOGIN_SUCCESS = "login_success", "Login success"
        LOGIN_FAILED = "login_failed", "Login failed"
        ACCESS_BLOCKED = "access_blocked", "Access blocked"

    ip_address = models.GenericIPAddressField(db_index=True)
    event_type = models.CharField(max_length=20, choices=EventType.choices, db_index=True)
    path = models.CharField(max_length=512, blank=True)
    username = models.CharField(max_length=150, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ip_address} — {self.get_event_type_display()} — {self.path}"


class BlockedIP(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    reason = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    blocked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blocked_ips",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        status = "active" if self.is_active else "inactive"
        return f"{self.ip_address} ({status})"
