from django.db.models import Count, Avg, F, Q, ExpressionWrapper, DurationField
from apps.correspondence.models import Correspondence
import uuid as uuid_lib
from datetime import date
from calendar import monthrange
from django.utils import timezone
from django.db import transaction
from rest_framework.exceptions import ValidationError as DRFValidationError
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


def resolve_period(period_type, year=None, month=None, start_date=None, end_date=None):
    if period_type == "monthly":
        if not year or not month:
            raise DRFValidationError({"detail": "Monthly reports require year and month."})
        start = date(int(year), int(month), 1)
        end = date(int(year), int(month), monthrange(int(year), int(month))[1])
        label = start.strftime("%B %Y")
        period_tag = start.strftime("%Y-%m")
    elif period_type == "annual":
        if not year:
            raise DRFValidationError({"detail": "Annual reports require year."})
        start = date(int(year), 1, 1)
        end = date(int(year), 12, 31)
        label = str(year)
        period_tag = str(year)
    elif period_type == "custom":
        if not start_date or not end_date:
            raise DRFValidationError({"detail": "Custom reports require start_date and end_date."})
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        if start > end:
            raise DRFValidationError({"detail": "start_date must not be after end_date."})
        label = f"{start.isoformat()} to {end.isoformat()}"
        period_tag = f"{start.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}"
    else:
        raise DRFValidationError({"detail": "period_type must be one of: monthly, annual, custom."})

    return {
        "type": period_type, "start_date": start.isoformat(), "end_date": end.isoformat(),
        "label": label, "_tag": period_tag,
    }


TYPE_SLUGS = {
    "OFFICE_PERFORMANCE": "PERFORMANCE",
    "OVERDUE": "OVERDUE",
    "PENDING_AGEING": "PENDING-AGEING",
    "STAFF_CONTRIBUTION": "STAFF-CONTRIBUTION",
}


def generate_report_reference(office, report_type, period, preview=False):
    from .models import FormalReport

    slug = TYPE_SLUGS.get(report_type, "REPORT")
    base_ref = f"MRH-{office.code}-{slug}-{period['_tag']}"

    if preview:
        return f"{base_ref}-PREVIEW"

    existing_count = FormalReport.objects.filter(
        office=office, report_type=report_type,
        period_type=period["type"], period_start=period["start_date"], period_end=period["end_date"],
    ).count()
    version = existing_count + 1
    return f"{base_ref}-V{version}"


def _office_qs_for_period(office, start_date, end_date):
    return Correspondence.objects.filter(current_office=office, received_at__date__range=[start_date, end_date])


def formal_office_performance(office, start_date, end_date):
    qs = _office_qs_for_period(office, start_date, end_date)
    total = qs.count()
    completed = qs.filter(status=Correspondence.Status.COMPLETED).count()
    filed = qs.filter(status=Correspondence.Status.FILED).count()
    overdue = qs.filter(status=Correspondence.Status.OVERDUE).count()

    avg_turnaround = qs.filter(resolved_at__isnull=False).aggregate(
        avg=Avg(ExpressionWrapper(F("resolved_at") - F("received_at"), output_field=DurationField()))
    )["avg"]

    status_breakdown = list(qs.values("status").annotate(count=Count("id")))
    type_breakdown = list(qs.values("type").annotate(count=Count("id")))
    priority_breakdown = list(qs.values("priority").annotate(count=Count("id")))

    open_qs = qs.exclude(status__in=[Correspondence.Status.COMPLETED, Correspondence.Status.FILED])
    now = timezone.now()
    stage_stats = {}
    for item in open_qs:
        stage = item.current_stage or "Unspecified"
        days = (now - item.received_at).days
        s = stage_stats.setdefault(stage, {"stage": stage, "count": 0, "total_days": 0})
        s["count"] += 1
        s["total_days"] += days
    bottlenecks = sorted(
        [{"stage": s["stage"], "count": s["count"], "avg_days_pending": round(s["total_days"] / s["count"], 1)}
         for s in stage_stats.values()],
        key=lambda x: (-x["count"], -x["avg_days_pending"]),
    )

    return {
        "summary": {
            "received": total,
            "completed": completed,
            "filed": filed,
            "pending": total - completed - filed,
            "overdue": overdue,
            "completion_rate": round((completed / total) * 100, 1) if total else 0,
            "avg_turnaround_days": round(avg_turnaround.total_seconds() / 86400, 1) if avg_turnaround else None,
        },
        "status_breakdown": status_breakdown,
        "type_breakdown": type_breakdown,
        "priority_breakdown": priority_breakdown,
        "ageing_summary": backlog_aging(office)["bands"],
        "overdue_summary": {"total_overdue": overdue},
        "staff_contribution_summary": staff_contribution(office, start_date, end_date),
        "bottlenecks": bottlenecks,
    }


def formal_overdue(office, start_date, end_date):
    """Any record where the deadline was missed, whether still open or since completed."""
    now = timezone.now()
    qs = Correspondence.objects.filter(current_office=office, deadline__isnull=False).filter(
        Q(resolved_at__isnull=True, deadline__lt=now) |
        Q(resolved_at__isnull=False, resolved_at__gt=F("deadline"))
    ).select_related()

    items = []
    for item in qs:
        last_movement = item.movements.order_by("-timestamp").first()
        overdue_reference_point = item.resolved_at or now
        items.append({
            "reference_number": item.reference_number,
            "subject": item.subject,
            "date_received": item.received_at.date().isoformat(),
            "due_date": item.deadline.date().isoformat(),
            "current_stage": item.current_stage,
            "current_status": item.status,
            "days_pending": (now - item.received_at).days,
            "days_overdue": (overdue_reference_point - item.deadline).days,
            "last_action_date": last_movement.timestamp.isoformat() if last_movement else None,
            "last_action_by": last_movement.actor.email if last_movement and last_movement.actor else None,
        })

    bands = {"1-7": 0, "8-14": 0, "15-30": 0, "30_plus": 0}
    for item in items:
        d = item["days_overdue"]
        if d <= 7:
            bands["1-7"] += 1
        elif d <= 14:
            bands["8-14"] += 1
        elif d <= 30:
            bands["15-30"] += 1
        else:
            bands["30_plus"] += 1

    oldest = max(items, key=lambda i: i["days_overdue"], default=None)
    return {
        "overdue_summary": {
            "total_overdue": len(items),
            "bands": bands,
            "oldest_overdue_item": oldest["reference_number"] if oldest else None,
        },
        "items": items,
    }


def formal_pending_ageing(office, start_date, end_date):
    now = timezone.now()
    qs = Correspondence.objects.filter(current_office=office).exclude(
        status__in=[Correspondence.Status.COMPLETED, Correspondence.Status.FILED]
    )

    items = []
    bands = {"0-2_days": 0, "3-7_days": 0, "8_plus_days": 0}
    for item in qs:
        age = (now - item.received_at).days
        band = "0-2_days" if age <= 2 else "3-7_days" if age <= 7 else "8_plus_days"
        bands[band] += 1
        last_movement = item.movements.order_by("-timestamp").first()
        items.append({
            "reference_number": item.reference_number,
            "subject": item.subject,
            "current_office": {"id": str(office.id), "name": office.name, "code": office.code},
            "priority": item.priority,
            "current_stage": item.current_stage,
            "status": item.status,
            "days_pending": age,
            "last_action_date": last_movement.timestamp.isoformat() if last_movement else None,
        })

    return {"ageing_bands": bands, "items": items}


CALCULATORS = {
    "OFFICE_PERFORMANCE": formal_office_performance,
    "OVERDUE": formal_overdue,
    "PENDING_AGEING": formal_pending_ageing,
    "STAFF_CONTRIBUTION": lambda office, start, end: {"contributors": staff_contribution(office, start, end)},
}


def build_formal_report_data(office, report_type, period, preview=True):
    calculator = CALCULATORS.get(report_type)
    if calculator is None:
        raise DRFValidationError({"report_type": f"Unknown report type: {report_type}"})

    data = calculator(office, period["start_date"], period["end_date"])
    reference = generate_report_reference(office, report_type, period, preview=preview)

    return {
        "report_type": report_type,
        "report_reference": reference,
        "office": {"id": str(office.id), "name": office.name, "code": office.code, "status": office.status},
        "period": {k: v for k, v in period.items() if not k.startswith("_")},
        "generated_at": timezone.now().isoformat(),
        **data,
    }


@transaction.atomic
def generate_formal_report(*, office, report_type, period, observations, recommendations, generated_by):
    from .models import FormalReport

    data = build_formal_report_data(office, report_type, period, preview=False)
    reference = data["report_reference"]

    data["generated_by"] = {
        "id": str(generated_by.id),
        "name": f"{generated_by.first_name} {generated_by.last_name}".strip() or generated_by.email,
        "role": generated_by.role}
    data["observations"] = observations
    data["recommendations"] = recommendations

    report = FormalReport.objects.create(
        report_reference=reference,
        report_type=report_type,
        office=office,
        period_type=period["type"],
        period_start=period["start_date"],
        period_end=period["end_date"],
        generated_by=generated_by,
        observations=observations,
        recommendations=recommendations,
        snapshot=data,
    )
    return report