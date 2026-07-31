import re
import secrets
from django.db import transaction
from .models import User, Office


def generate_user_email(first_name, last_name, office):
    """firstname.lastname@officecode.mrh.gov.gh - adds a number if that's taken."""
    base = re.sub(r"[^a-z.]", "", f"{first_name}.{last_name}".lower())
    domain = f"{office.code.lower()}.mrh.gov.gh"
    email = f"{base}@{domain}"
    suffix = 1
    while User.objects.filter(email=email).exists():
        suffix += 1
        email = f"{base}{suffix}@{domain}"
    return email


def generate_password(length=8):
    """A readable random password - letters and digits, no visually-confusable characters."""
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@transaction.atomic
def create_user(*, first_name, last_name, role, office, created_by):
    email = generate_user_email(first_name, last_name, office)
    raw_password = generate_password()

    user = User(
        username=email.split("@")[0],
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=role,
        office=office,
    )
    user.set_password(raw_password)
    user.save()
    return user, raw_password


@transaction.atomic
def regenerate_user_password(*, user, changed_by):
    from apps.audit.models import AuditLog

    raw_password = generate_password()
    user.set_password(raw_password)
    user.save(update_fields=["password"])

    AuditLog.objects.create(
        action_type=AuditLog.ActionType.SECURITY,
        title="User password regenerated",
        description=f"Password reset for {user.email} by {changed_by.email}",
        actor=changed_by,
        office=user.office,
    )
    return raw_password