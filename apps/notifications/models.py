from django.db import models
import uuid
from django.conf import settings
# Create your models here.

class Notification(models.Model):
    class Type(models.TextChoices):
        NEW = "New", "New"
        FORWARD = "Forward", "Forward"
        REMINDER = "Reminder", "Reminder"
        OVERDUE = "Overdue", "Overdue"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    correspondence = models.ForeignKey("correspondence.Correspondence", on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    type = models.CharField(max_length=20, choices=Type.choices)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read"])]