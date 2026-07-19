from django.db.models import Count, Avg, F, Q, ExpressionWrapper, DurationField
from apps.correspondence.models import Correspondence


def office_summary(office, start, end):
    qs = Correspondence.objects.filter(current_office=office, received_at__range=[start, end])
    return {
        "total": qs.count(),
        "by_type": list(qs.values("type").annotate(count=Count("id"))),
        "by_status": list(qs.values("status").annotate(count=Count("id"))),
        "avg_turnaround_hours": qs.filter(resolved_at__isnull=False).aggregate(
            avg=Avg(ExpressionWrapper(F("resolved_at") - F("received_at"), output_field=DurationField()))
        )["avg"],
    }


def user_workload(office, start, end):
    qs = Correspondence.objects.filter(current_office=office, received_at__range=[start, end])
    return list(
        qs.values("assigned_to__id", "assigned_to__email")
        .annotate(
            assigned=Count("id"),
            completed=Count("id", filter=Q(status=Correspondence.Status.COMPLETED)),
            open=Count("id", filter=~Q(status=Correspondence.Status.COMPLETED)),
            overdue=Count("id", filter=Q(status=Correspondence.Status.OVERDUE)),
        )
    )


def backlog_aging(office):
    from django.utils import timezone
    now = timezone.now()
    open_items = Correspondence.objects.filter(
        current_office=office
    ).exclude(status=Correspondence.Status.COMPLETED)

    buckets = {"0-2_days": 0, "3-7_days": 0, "7_plus_days": 0}
    for item in open_items:
        age_days = (now - item.received_at).days
        if age_days <= 2:
            buckets["0-2_days"] += 1
        elif age_days <= 7:
            buckets["3-7_days"] += 1
        else:
            buckets["7_plus_days"] += 1
    return buckets


def type_trend(office, months=6):
    from django.utils import timezone
    from dateutil.relativedelta import relativedelta

    start = timezone.now() - relativedelta(months=months)
    qs = Correspondence.objects.filter(current_office=office, received_at__gte=start)
    return list(
        qs.annotate(month=F("received_at__month"), year=F("received_at__year"))
        .values("year", "month", "type")
        .annotate(count=Count("id"))
        .order_by("year", "month")
    )