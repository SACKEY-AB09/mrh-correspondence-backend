from django.db import models

# Create your models here.
# apps/accounts/models.py
import uuid
from django.contrib.auth.models import AbstractUser



class Office(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "Active", "Active"
        INACTIVE = "Inactive", "Inactive"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Role(models.TextChoices):
        OFFICE_USER = "OFFICE_USER", "Office User"
        ADMIN = "ADMIN", "System Administrator"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=50, choices=Role.choices, default=Role.OFFICE_USER)
    office = models.ForeignKey(Office, on_delete=models.PROTECT, related_name="users", null=True, blank=True)
    must_reset_password = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email


class UserPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="preferences")
    deadline_reminders = models.BooleanField(default=True)
    overdue_alerts = models.BooleanField(default=True)
    compact_list_view = models.BooleanField(default=False)

    def __str__(self):
        return f"Preferences for {self.user.email}"