from django.db import models

# Create your models here.
import uuid
from django.conf import settings
from django.db import models


class Correspondence(models.Model):
    class Type(models.TextChoices):
        CONTRACT = "Contract", "Contract"
        LETTER = "Letter", "Letter"
        MEMO = "Memo", "Memo"
        REPORT = "Report", "Report"

    class Priority(models.TextChoices):
        NORMAL = "Normal", "Normal"
        HIGH = "High", "High"
        URGENT = "Urgent", "Urgent"

    class Direction(models.TextChoices):
        INCOMING = "Incoming", "Incoming"
        INTERNAL = "Internal", "Internal"

    class Status(models.TextChoices):
        REGISTERED = "Registered", "Registered"
        IN_PROGRESS = "In Progress", "In Progress"
        AWAITING_ACTION = "Awaiting Action", "Awaiting Action"
        FORWARDED = "Forwarded", "Forwarded"
        COMPLETED = "Completed", "Completed"
        FILED = "Filed", "Filed"
        OVERDUE = "Overdue", "Overdue"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference_number = models.CharField(max_length=50, unique=True, editable=False)
    type = models.CharField(max_length=20, choices=Type.choices)
    subject = models.CharField(max_length=255)
    sender = models.CharField(max_length=255)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    direction = models.CharField(max_length=10, choices=Direction.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REGISTERED)

    current_office = models.ForeignKey("accounts.Office", on_delete=models.PROTECT, related_name="correspondence")
    current_stage = models.CharField(max_length=100, blank=True)
    registered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="registered_correspondence")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_correspondence")

    deadline = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["type"]),
            models.Index(fields=["current_office"]),
            models.Index(fields=["reference_number"]),
        ]

    def __str__(self):
        return f"{self.reference_number} — {self.subject}"


class CorrespondenceMovement(models.Model):
    class ActionType(models.TextChoices):
        REGISTERED = "Registered", "Registered"
        FORWARDED = "Forwarded", "Forwarded"
        STAGE_UPDATED = "Stage Updated", "Stage Updated"
        COMPLETED = "Completed", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    correspondence = models.ForeignKey(Correspondence, on_delete=models.CASCADE, related_name="movements")
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    from_office = models.ForeignKey("accounts.Office", on_delete=models.SET_NULL, null=True, blank=True, related_name="movements_from")
    to_office = models.ForeignKey("accounts.Office", on_delete=models.SET_NULL, null=True, blank=True, related_name="movements_to")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    note = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]


class Attachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    correspondence = models.ForeignKey(Correspondence, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="attachments/%Y/%m/")
    original_filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class Note(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    correspondence = models.ForeignKey(Correspondence, on_delete=models.CASCADE, related_name="notes")
    text = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]