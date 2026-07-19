from django.db import models
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