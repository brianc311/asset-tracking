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
