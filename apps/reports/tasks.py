from celery import shared_task
from django.utils import timezone
from django.db.models import Count, Avg, F, ExpressionWrapper, DurationField
from apps.accounts.models import Office
from apps.correspondence.models import Correspondence
from .models import ReportSnapshot
from django.db.models import Q

@shared_task
def build_daily_report_snapshots():
    """Roll up yesterday's correspondence activity into ReportSnapshot rows, per office+type."""
    yesterday = (timezone.now() - timezone.timedelta(days=1)).date()

    created = 0
    for office in Office.objects.all():
        qs = Correspondence.objects.filter(current_office=office, received_at__date=yesterday)
        by_type = qs.values("type").annotate(
            registered=Count("id"),
            completed=Count("id", filter=models_Q_completed()),
        )
        for row in by_type:
            avg = qs.filter(type=row["type"], resolved_at__isnull=False).aggregate(
                avg=Avg(ExpressionWrapper(F("resolved_at") - F("received_at"), output_field=DurationField()))
            )["avg"]
            ReportSnapshot.objects.update_or_create(
                office=office, date=yesterday, correspondence_type=row["type"],
                defaults={
                    "count_registered": row["registered"],
                    "count_completed": row["completed"],
                    "avg_turnaround_hours": avg.total_seconds() / 3600 if avg else None,
                },
            )
            created += 1
    return f"Built {created} report snapshots for {yesterday}."


def models_Q_completed():
    return Q(status=Correspondence.Status.COMPLETED)