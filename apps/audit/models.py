from django.db import models
import uuid
from django.conf import settings
# Create your models here.
class AuditLog(models.Model):
    class ActionType(models.TextChoices):
        REGISTERED = "Registered", "Registered"
        FORWARDED = "Forwarded", "Forwarded"
        STAGE_UPDATED = "Stage Updated", "Stage Updated"
        COMPLETED = "Completed", "Completed"
        SECURITY = "Security", "Security"
        REPORT_GENERATED = "Report Generated", "Report Generated"  
        REPORT_VIEWED = "Report Viewed", "Report Viewed" 

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    title = models.CharField(max_length=255)
    description = models.TextField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    office = models.ForeignKey("accounts.Office", on_delete=models.SET_NULL, null=True, blank=True)
    correspondence = models.ForeignKey("correspondence.Correspondence", on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [models.Index(fields=["action_type"]), models.Index(fields=["timestamp"])]