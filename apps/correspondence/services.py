from django.db import transaction, IntegrityError
from django.utils import timezone
from .models import Correspondence, CorrespondenceMovement
from .signals import (
    correspondence_registered, correspondence_forwarded,
    correspondence_stage_updated, correspondence_completed, correspondence_filed,
)

def generate_reference_number(office):
    """Format: OFFICECODE-YEAR-SEQUENCE, e.g. LEG-2026-0007.
    Looks at the highest sequence number actually in use for this office+year,
    rather than counting rows — this is robust against any historical
    inconsistency in the data (e.g. records created outside the normal flow)."""
    year = timezone.now().year
    prefix = f"{office.code}-{year}-"

    existing_numbers = Correspondence.objects.filter(
        reference_number__startswith=prefix
    ).values_list("reference_number", flat=True)

    max_seq = 0
    for ref in existing_numbers:
        suffix = ref[len(prefix):]
        if suffix.isdigit():
            max_seq = max(max_seq, int(suffix))

    return f"{prefix}{max_seq + 1:04d}"


@transaction.atomic
def register_correspondence(*, data, office, actor):
    data = dict(data)
    data.pop("current_office", None)

    for attempt in range(5):
        reference_number = generate_reference_number(office)
        try:
            with transaction.atomic():
                correspondence = Correspondence.objects.create(
                    reference_number=reference_number,
                    registered_by=actor,
                    current_office=office,
                    status=Correspondence.Status.REGISTERED,
                    **data,
                )
            break
        except IntegrityError:
            if attempt == 4:
                raise
            continue

    CorrespondenceMovement.objects.create(
        correspondence=correspondence,
        action_type=CorrespondenceMovement.ActionType.REGISTERED,
        to_office=office,
        actor=actor,
    )
    correspondence_registered.send(sender=Correspondence, correspondence=correspondence, actor=actor)
    return correspondence


@transaction.atomic
def forward_correspondence(*, correspondence, to_office, actor, note=""):
    from_office = correspondence.current_office
    correspondence.current_office = to_office
    correspondence.status = Correspondence.Status.FORWARDED
    correspondence.save(update_fields=["current_office", "status"])

    CorrespondenceMovement.objects.create(
        correspondence=correspondence,
        action_type=CorrespondenceMovement.ActionType.FORWARDED,
        from_office=from_office,
        to_office=to_office,
        actor=actor,
        note=note,
    )
    correspondence_forwarded.send(sender=Correspondence, correspondence=correspondence, actor=actor, from_office=from_office, to_office=to_office, note=note)
    return correspondence



@transaction.atomic
def update_stage(*, correspondence, new_stage, actor, note=""):
    previous_stage = correspondence.current_stage
    correspondence.current_stage = new_stage
    correspondence.status = Correspondence.Status.IN_PROGRESS
    correspondence.save(update_fields=["current_stage", "status"])

    CorrespondenceMovement.objects.create(
        correspondence=correspondence,
        action_type=CorrespondenceMovement.ActionType.STAGE_UPDATED,
        previous_stage=previous_stage,
        new_stage=new_stage,
        actor=actor,
        note=note,
    )
    correspondence_stage_updated.send(sender=Correspondence, correspondence=correspondence, actor=actor, note=note)
    return correspondence

@transaction.atomic
def complete_correspondence(*, correspondence, actor, note=""):
    correspondence.status = Correspondence.Status.COMPLETED
    correspondence.resolved_at = timezone.now()
    correspondence.save(update_fields=["status", "resolved_at"])

    CorrespondenceMovement.objects.create(
        correspondence=correspondence,
        action_type=CorrespondenceMovement.ActionType.COMPLETED,
        actor=actor,
        note=note,
    )
    correspondence_completed.send(sender=Correspondence, correspondence=correspondence, actor=actor, note=note)
    return correspondence

@transaction.atomic
def file_correspondence(*, correspondence, actor, note=""):
    correspondence.status = Correspondence.Status.FILED
    correspondence.save(update_fields=["status"])

    CorrespondenceMovement.objects.create(
        correspondence=correspondence,
        action_type=CorrespondenceMovement.ActionType.FILED, 
        actor=actor,
        note=note or "Marked as filed",
    )
    correspondence_filed.send(sender=Correspondence, correspondence=correspondence, actor=actor, note=note)
    return correspondence
