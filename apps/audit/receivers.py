from django.dispatch import receiver
from apps.correspondence.signals import (
    correspondence_registered, correspondence_forwarded,
    correspondence_stage_updated, correspondence_completed, correspondence_filed,
)
from .models import AuditLog


@receiver(correspondence_registered)
def log_registration(sender, correspondence, actor, **kwargs):
    AuditLog.objects.create(
        action_type=AuditLog.ActionType.REGISTERED,
        title=f"Correspondence registered: {correspondence.reference_number}",
        description=f"{actor.email} registered '{correspondence.subject}'",
        actor=actor, office=correspondence.current_office, correspondence=correspondence,
    )


@receiver(correspondence_forwarded)
def log_forward(sender, correspondence, actor, from_office, to_office, note, **kwargs):
    AuditLog.objects.create(
        action_type=AuditLog.ActionType.FORWARDED,
        title=f"Forwarded: {correspondence.reference_number}",
        description=f"{actor.email} forwarded from {from_office} to {to_office}. {note}",
        actor=actor, office=to_office, correspondence=correspondence,
    )


@receiver(correspondence_stage_updated)
def log_stage_update(sender, correspondence, actor, note, **kwargs):
    AuditLog.objects.create(
        action_type=AuditLog.ActionType.STAGE_UPDATED,
        title=f"Stage updated: {correspondence.reference_number}",
        description=f"{actor.email} set stage to '{correspondence.current_stage}'. {note}",
        actor=actor, office=correspondence.current_office, correspondence=correspondence,
    )


@receiver(correspondence_completed)
def log_completion(sender, correspondence, actor, note, **kwargs):
    AuditLog.objects.create(
        action_type=AuditLog.ActionType.COMPLETED,
        title=f"Completed: {correspondence.reference_number}",
        description=f"{actor.email} marked '{correspondence.subject}' as completed. {note}",
        actor=actor, office=correspondence.current_office, correspondence=correspondence,
    )