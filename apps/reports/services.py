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


def staff_contribution(office, start, end):
    """Action-based contribution per user, built from actual audited actions —
    not correspondence ownership, since correspondence belongs to offices, not people."""
    from apps.correspondence.models import CorrespondenceMovement, Note, Attachment, Correspondence

    movements = CorrespondenceMovement.objects.filter(
        actor__office=office, timestamp__range=[start, end]
    ).select_related("actor")

    contributions = {}

    def bucket(user):
        key = str(user.id)
        if key not in contributions:
            contributions[key] = {
                "user_id": key,
                "user_email": user.email,
                "registered": 0,
                "stage_updates": 0,
                "forwarded": 0,
                "completed": 0,
                "filed": 0,
                "notes_added": 0,
                "attachments_uploaded": 0,
                "total_actions": 0,
            }
        return contributions[key]

    action_field_map = {
        CorrespondenceMovement.ActionType.REGISTERED: "registered",
        CorrespondenceMovement.ActionType.FORWARDED: "forwarded",
        CorrespondenceMovement.ActionType.STAGE_UPDATED: "stage_updates",
        CorrespondenceMovement.ActionType.COMPLETED: "completed",
    }

    for m in movements:
        if m.actor is None:
            continue
        entry = bucket(m.actor)
        field = action_field_map.get(m.action_type)
        if field:
            entry[field] += 1
        entry["total_actions"] += 1

    notes = Note.objects.filter(author__office=office, created_at__range=[start, end]).select_related("author")
    for n in notes:
        if n.author is None:
            continue
        entry = bucket(n.author)
        entry["notes_added"] += 1
        entry["total_actions"] += 1

    attachments = Attachment.objects.filter(
        uploaded_by__office=office, uploaded_at__range=[start, end]
    ).select_related("uploaded_by")
    for a in attachments:
        if a.uploaded_by is None:
            continue
        entry = bucket(a.uploaded_by)
        entry["attachments_uploaded"] += 1
        entry["total_actions"] += 1

    return list(contributions.values())


def backlog_aging(office):
    from django.utils import timezone
    now = timezone.now()
    open_items = Correspondence.objects.filter(
        current_office=office
    ).exclude(status=Correspondence.Status.COMPLETED)

    counts = {"0-2_days": 0, "3-7_days": 0, "8_plus_days": 0}
    for item in open_items:
        age_days = (now - item.received_at).days
        if age_days <= 2:
            counts["0-2_days"] += 1
        elif age_days <= 7:
            counts["3-7_days"] += 1
        else:
            counts["8_plus_days"] += 1

    return {
        "bands": [
            {"key": "0-2_days", "label": "0-2 days", "min_days": 0, "max_days": 2, "count": counts["0-2_days"]},
            {"key": "3-7_days", "label": "3-7 days", "min_days": 3, "max_days": 7, "count": counts["3-7_days"]},
            {"key": "8_plus_days", "label": "8+ days", "min_days": 8, "max_days": None, "count": counts["8_plus_days"]},
        ],
        "total_open": sum(counts.values()),
    }


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