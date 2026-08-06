from django.db.models import Q
from rest_framework.exceptions import PermissionDenied
from .models import CorrespondenceMovement


def office_has_current_access(user, correspondence):
    """An office has full access to a correspondence record only if the most recent
    movement involving that office brought the record TO them — i.e. they currently
    hold it, or it's been forwarded back to them since they last sent it elsewhere."""
    office = user.office
    if office is None:
        return False

    last_movement = (
        CorrespondenceMovement.objects.filter(correspondence=correspondence)
        .filter(Q(from_office=office) | Q(to_office=office))
        .order_by("-timestamp")
        .first()
    )
    if last_movement is None:
        return correspondence.current_office_id == office.id
    return last_movement.to_office_id == office.id


def enforce_office_access(user, correspondence):
    """Admins retain read-only oversight access everywhere (per fix #2 — oversight, not
    workflow control). Non-admins are blocked from full record access once they've
    forwarded it away, until it's sent back to them."""
    if user.role == user.Role.ADMIN:
        return
    if not office_has_current_access(user, correspondence):
        raise PermissionDenied(
            "This correspondence is no longer held by your office. It remains visible in "
            "your forwarded history, but full details are unavailable unless it is forwarded back to you."
        )