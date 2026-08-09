from django.db import models
from django.conf import settings
import uuid
# Create your models here.

from django.db import models


class ReportSnapshot(models.Model):
    """One row per office, per day, per correspondence type — a precomputed rollup.
    Populated by a nightly Celery task (added later). Empty for now; live queries
    in services.py cover everything until that's wired in."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    office = models.ForeignKey("accounts.Office", on_delete=models.CASCADE, related_name="report_snapshots")
    date = models.DateField()
    correspondence_type = models.CharField(max_length=30)
    count_registered = models.PositiveIntegerField(default=0)
    count_completed = models.PositiveIntegerField(default=0)
    count_overdue = models.PositiveIntegerField(default=0)
    avg_turnaround_hours = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ("office", "date", "correspondence_type")
        indexes = [models.Index(fields=["office", "date"])]

class FormalReport(models.Model):
    class ReportType(models.TextChoices):
        OFFICE_PERFORMANCE = "OFFICE_PERFORMANCE", "Office Performance"
        OVERDUE = "OVERDUE", "Overdue Documents"
        PENDING_AGEING = "PENDING_AGEING", "Pending and Ageing"
        STAFF_CONTRIBUTION = "STAFF_CONTRIBUTION", "Staff Contribution"

    class PeriodType(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        ANNUAL = "annual", "Annual"
        CUSTOM = "custom", "Custom"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_reference = models.CharField(max_length=100, unique=True, editable=False)
    report_type = models.CharField(max_length=30, choices=ReportType.choices)
    office = models.ForeignKey("accounts.Office", on_delete=models.PROTECT, related_name="formal_reports")
    period_type = models.CharField(max_length=10, choices=PeriodType.choices)
    period_start = models.DateField()
    period_end = models.DateField()
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    generated_at = models.DateTimeField(auto_now_add=True)
    observations = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    snapshot = models.JSONField()

    class Meta:
        ordering = ["-generated_at"]
        indexes = [
        models.Index(fields=["office", "report_type", "period_start", "period_end"]),
    ]
        
        

    def __str__(self):
        return self.report_reference