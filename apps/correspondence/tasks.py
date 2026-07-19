from celery import shared_task
from django.utils import timezone
from .models import Correspondence


@shared_task
def detect_overdue_correspondence():
    """Flip any open correspondence past its deadline to Overdue status."""
    now = timezone.now()
    overdue_items = Correspondence.objects.filter(
        deadline__lt=now,
        deadline__isnull=False,
    ).exclude(
        status__in=[Correspondence.Status.COMPLETED, Correspondence.Status.FILED, Correspondence.Status.OVERDUE]
    )
    count = overdue_items.update(status=Correspondence.Status.OVERDUE)
    return f"Marked {count} correspondence records as overdue."


@shared_task
def send_deadline_reminders():
    """Notify assignees of correspondence due within the next 24 hours."""
    from apps.notifications.models import Notification

    now = timezone.now()
    soon = now + timezone.timedelta(hours=24)
    upcoming = Correspondence.objects.filter(
        deadline__range=[now, soon],
        assigned_to__isnull=False,
    ).exclude(status=Correspondence.Status.COMPLETED)

    created = 0
    for item in upcoming:
        Notification.objects.create(
            recipient=item.assigned_to,
            correspondence=item,
            type=Notification.Type.REMINDER,
            title=f"Deadline approaching: {item.reference_number}",
            message=f"'{item.subject}' is due by {item.deadline.strftime('%Y-%m-%d %H:%M')}.",
        )
        created += 1
    return f"Sent {created} deadline reminders."